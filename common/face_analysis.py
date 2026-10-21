"""
InsightFace analysis for ComfyUI-API-DockerCPU, via onnxruntime directly
(no insightface package).

- FaceAnalyze:    SCRFD detection (e.g. buffalo_l det_10g.onnx) + ArcFace
                  embeddings (e.g. w600k_r50.onnx). Outputs native BOUNDING_BOX.
- FaceSimilarity: Cosine similarity of a detected face against a reference
                  FACE_ANALYSIS or a folder of reference images / .npy embeddings.

Runs on CPU; uses CUDA/ROCm/DirectML automatically when onnxruntime exposes them.
Pre/post-processing follows insightface model_zoo/scrfd.py and arcface_onnx.py
and utils/face_align.py (arcface template + similarity transform).
"""

import json
import os
import threading

import numpy as np
from PIL import Image, ImageOps

import folder_paths

try:
    import onnxruntime as ort
except ImportError:
    ort = None

FOLDER_NAME = "insightface"
DEFAULT_DETECTOR = "det_10g.onnx"
DEFAULT_RECOGNIZER = "w600k_r50.onnx"
PROVIDER_OPTIONS = ["auto", "cpu"]
# GPU providers tried in order by 'auto'. TensorRT is left out: its engine build is slow on first use.
_GPU_PROVIDERS = ("CUDAExecutionProvider", "ROCMExecutionProvider", "DmlExecutionProvider")

# Five-point ArcFace alignment template for a 112x112 crop (insightface utils/face_align.py).
ARCFACE_DST = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
     [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Register models/insightface unless extra_model_paths.yaml already did.
if FOLDER_NAME not in folder_paths.folder_names_and_paths:
    folder_paths.add_model_folder_path(FOLDER_NAME, os.path.join(folder_paths.models_dir, FOLDER_NAME))


def _onnx_models():
    files = [f for f in folder_paths.get_filename_list(FOLDER_NAME) if f.lower().endswith(".onnx")]
    return files or ["(no .onnx files in models/insightface)"]


def _default_model(files, basename):
    for f in files:
        if f.replace("\\", "/").rsplit("/", 1)[-1] == basename:
            return f
    return files[0]


def _require_ort():
    if ort is None:
        raise RuntimeError("onnxruntime is not installed. Install 'onnxruntime' (CPU) or 'onnxruntime-gpu'.")


def _providers(choice):
    if choice == "cpu":
        return ["CPUExecutionProvider"]
    available = ort.get_available_providers()
    return [p for p in _GPU_PROVIDERS if p in available][:1] + ["CPUExecutionProvider"]


_sessions = {}
_sessions_lock = threading.Lock()


def _session(model_name, provider):
    _require_ort()
    path = folder_paths.get_full_path_or_raise(FOLDER_NAME, model_name)
    providers = _providers(provider)
    key = (path, tuple(providers))
    with _sessions_lock:
        if key not in _sessions:
            _sessions[key] = ort.InferenceSession(path, providers=providers)
        return _sessions[key]


# ---------------------------------------------------------------- detection (SCRFD)

def _nms(dets, thresh):
    x1, y1, x2, y2, scores = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3], dets[:, 4]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = np.argsort(-scores, kind="stable")
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[np.where(ovr <= thresh)[0] + 1]
    return keep


def _detect(session, img, det_size, det_thresh, nms_thresh):
    """SCRFD detection on an RGB uint8 HxWx3 array.

    Returns (boxes Nx4 xyxy, scores N, kps Nx5x2) in original image pixels.
    """
    outputs = session.get_outputs()
    if len(outputs) != 9:
        raise ValueError(f"Detector has {len(outputs)} outputs; expected a 9-output SCRFD model with keypoints (e.g. det_10g.onnx)")
    fmc, strides, num_anchors = 3, (8, 16, 32), 2

    # Letterbox: keep aspect ratio, place at top-left of a det_size square.
    h, w = img.shape[:2]
    if h / w > 1.0:
        new_h, new_w = det_size, int(det_size * w / h)
    else:
        new_w, new_h = det_size, int(det_size * h / w)
    new_w, new_h = max(1, new_w), max(1, new_h)
    det_scale = new_h / h
    canvas = np.zeros((det_size, det_size, 3), dtype=np.float32)
    canvas[:new_h, :new_w] = np.asarray(Image.fromarray(img).resize((new_w, new_h), Image.BILINEAR), dtype=np.float32)
    blob = ((canvas - 127.5) / 128.0).transpose(2, 0, 1)[None]

    net_outs = session.run([o.name for o in outputs], {session.get_inputs()[0].name: blob})

    boxes, scores, kpss = [], [], []
    for idx, stride in enumerate(strides):
        s = net_outs[idx].reshape(-1)
        bbox_preds = net_outs[idx + fmc].reshape(-1, 4) * stride
        kps_preds = net_outs[idx + fmc * 2].reshape(-1, 10) * stride
        fh, fw = det_size // stride, det_size // stride
        centers = (np.stack(np.mgrid[:fh, :fw][::-1], axis=-1).astype(np.float32) * stride).reshape(-1, 2)
        centers = np.repeat(centers, num_anchors, axis=0)
        pos = np.where(s >= det_thresh)[0]
        c = centers[pos]
        d = bbox_preds[pos]
        boxes.append(np.stack([c[:, 0] - d[:, 0], c[:, 1] - d[:, 1], c[:, 0] + d[:, 2], c[:, 1] + d[:, 3]], axis=-1))
        k = kps_preds[pos].reshape(-1, 5, 2)
        kpss.append(c[:, None, :] + k)
        scores.append(s[pos])

    boxes = np.concatenate(boxes) / det_scale
    kpss = np.concatenate(kpss) / det_scale
    scores = np.concatenate(scores)
    if scores.size == 0:
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32), np.zeros((0, 5, 2), np.float32)

    order = np.argsort(-scores, kind="stable")
    dets = np.hstack([boxes, scores[:, None]])[order]
    keep = _nms(dets, nms_thresh)
    return dets[keep, :4], dets[keep, 4], kpss[order][keep]


# ---------------------------------------------------------------- recognition (ArcFace)

def _similarity_transform(src, dst):
    """2x3 similarity transform mapping src points onto dst (Umeyama, with
    scaling), as skimage SimilarityTransform.estimate."""
    src = src.astype(np.float64)
    dst = dst.astype(np.float64)
    n = src.shape[0]
    src_mean, dst_mean = src.mean(0), dst.mean(0)
    src_d, dst_d = src - src_mean, dst - dst_mean
    cov = dst_d.T @ src_d / n
    d = np.ones(2)
    if np.linalg.det(cov) < 0:
        d[1] = -1
    U, S, Vt = np.linalg.svd(cov)
    R = U @ np.diag(d) @ Vt
    scale = (S * d).sum() / src_d.var(0).sum()
    t = dst_mean - scale * R @ src_mean
    return np.hstack([scale * R, t[:, None]])


def _align(img_pil, kps, size=112):
    M = _similarity_transform(kps, ARCFACE_DST * (size / 112.0))
    # PIL wants the inverse mapping (output pixel -> input pixel).
    inv = np.linalg.inv(np.vstack([M, [0, 0, 1]]))[:2]
    return img_pil.transform((size, size), Image.AFFINE, inv.flatten().tolist(), resample=Image.BILINEAR)


def _embed(session, img_pil, kps_list):
    if len(kps_list) == 0:
        return np.zeros((0, 512), np.float32)
    # One face per run: w600k_r50 declares a fixed {1, 512} output, so batching
    # works but makes onnxruntime log a shape warning for every call.
    input_name = session.get_inputs()[0].name
    feats = []
    for k in kps_list:
        crop = np.asarray(_align(img_pil, k), dtype=np.float32)
        blob = ((crop - 127.5) / 127.5).transpose(2, 0, 1)[None]
        feats.append(session.run(None, {input_name: blob})[0][0])
    feats = np.stack(feats)
    return feats / np.linalg.norm(feats, axis=1, keepdims=True).clip(min=1e-12)


SORT_OPTIONS = ["left_to_right", "score"]


def sort_left_to_right(bboxes):
    """Order {x, y, width, height} dicts by centre-x, then centre-y."""
    return sorted(bboxes, key=lambda b: (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2))


def _analyze_array(img, detector, recognizer, provider, det_size, det_thresh, nms_thresh, max_faces, sort="score"):
    """Faces in one RGB uint8 image. max_faces keeps the highest-scoring faces;
    sort then orders them ('score' = detection score, 'left_to_right')."""
    boxes, scores, kpss = _detect(_session(detector, provider), img, det_size, det_thresh, nms_thresh)
    if max_faces > 0:
        boxes, scores, kpss = boxes[:max_faces], scores[:max_faces], kpss[:max_faces]
    emb = _embed(_session(recognizer, provider), Image.fromarray(img), kpss)
    h, w = img.shape[:2]
    faces = []
    for box, score, kps, e in zip(boxes, scores, kpss, emb):
        x1, y1 = max(0.0, float(box[0])), max(0.0, float(box[1]))
        x2, y2 = min(float(w), float(box[2])), min(float(h), float(box[3]))
        faces.append({
            "bbox": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1, "label": "face", "score": float(score)},
            "score": float(score),
            "kps": kps.astype(np.float32),
            "embedding": e.astype(np.float32),
        })
    if sort == "left_to_right":
        order = sort_left_to_right([dict(f["bbox"], i=i) for i, f in enumerate(faces)])
        faces = [faces[b["i"]] for b in order]
    return faces


def _image_to_uint8(image):
    return np.clip(np.round(image[..., :3].cpu().numpy() * 255.0), 0, 255).astype(np.uint8)


class FaceAnalyze:
    """
    Detect faces (SCRFD) and compute 512-d ArcFace embeddings.

    sort orders faces in every output the same way, so face k is the same face
    in bboxes, scores, faces_json and face_analysis: left_to_right (bbox
    centre-x, then centre-y) or score (highest first).

    Outputs:
        bboxes:        Native BOUNDING_BOX list per frame ({x, y, width, height, label, score})
        face_analysis: FACE_ANALYSIS (per frame: list of faces with bbox, score, kps, embedding)
        face_count:    Faces found in the first frame (INT)
        scores:        JSON list per frame of detection scores (STRING)
        faces_json:    JSON list of {frame, index (1-based per frame), x, y, width, height, score} (STRING)
    """

    @classmethod
    def INPUT_TYPES(cls):
        models = _onnx_models()
        return {
            "required": {
                "image": ("IMAGE",),
                "detector": (models, {"default": _default_model(models, DEFAULT_DETECTOR), "tooltip": "SCRFD detector from models/insightface (det_10g.onnx)."}),
                "recognizer": (models, {"default": _default_model(models, DEFAULT_RECOGNIZER), "tooltip": "ArcFace recognizer from models/insightface (w600k_r50.onnx)."}),
                "det_threshold": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 1.0, "step": 0.01}),
                "nms_threshold": ("FLOAT", {"default": 0.4, "min": 0.01, "max": 1.0, "step": 0.01}),
                "det_size": ("INT", {"default": 640, "min": 160, "max": 2048, "step": 32, "tooltip": "Detector input size (multiple of 32)."}),
                "max_faces": ("INT", {"default": 0, "min": 0, "max": 256, "tooltip": "Keep the N highest-scoring faces per frame. 0 = all."}),
                "provider": (PROVIDER_OPTIONS, {"default": "auto", "tooltip": "auto uses CUDA/ROCm/DirectML when available, else CPU."}),
            },
            "optional": {
                "sort": (SORT_OPTIONS, {"default": "left_to_right", "tooltip": "Face order in every output: left_to_right (centre-x) or detection score."}),
            },
        }

    RETURN_TYPES = ("BOUNDING_BOX", "FACE_ANALYSIS", "INT", "STRING", "STRING")
    RETURN_NAMES = ("bboxes", "face_analysis", "face_count", "scores", "faces_json")
    FUNCTION = "analyze"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Detects faces with InsightFace SCRFD and computes ArcFace embeddings via onnxruntime (CPU or GPU)."

    def analyze(self, image, detector, recognizer, det_threshold=0.5, nms_threshold=0.4, det_size=640, max_faces=0, provider="auto",
                sort="left_to_right"):
        if det_size % 32:
            raise ValueError(f"det_size must be a multiple of 32, got {det_size}")
        frames = [
            _analyze_array(_image_to_uint8(frame), detector, recognizer, provider,
                           det_size, det_threshold, nms_threshold, max_faces, sort)
            for frame in image
        ]
        bboxes = [[f["bbox"] for f in faces] for faces in frames]
        scores = json.dumps([[round(f["score"], 4) for f in faces] for faces in frames])
        faces_json = json.dumps([
            {"frame": fi, "index": i + 1, **{k: round(f["bbox"][k], 1) for k in ("x", "y", "width", "height")},
             "score": round(f["score"], 4)}
            for fi, faces in enumerate(frames) for i, f in enumerate(faces)
        ])
        face_count = len(frames[0]) if frames else 0
        return (bboxes, {"frames": frames, "detector": detector, "recognizer": recognizer}, face_count, scores, faces_json)


# ---------------------------------------------------------------- similarity

_reference_cache = {}


def _load_reference_folder(folder, analysis_args):
    """Embeddings for every reference in folder: .npy files (512 floats) and
    images (largest face). Label is the subfolder name for files in a
    subfolder ('refs/Alice/1.jpg' -> 'Alice'), otherwise the file stem."""
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Reference folder not found: {folder}")
    refs = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            if ext != ".npy" and ext not in IMAGE_EXTENSIONS:
                continue
            rel_root = os.path.relpath(root, folder)
            label = os.path.splitext(name)[0] if rel_root == "." else rel_root.replace("\\", "/")
            st = os.stat(path)
            key = (path, st.st_size, st.st_mtime_ns, analysis_args)
            if key not in _reference_cache:
                _reference_cache[key] = _reference_embedding(path, ext, analysis_args)
            emb = _reference_cache[key]
            if emb is not None:
                refs.append((label, os.path.relpath(path, folder).replace("\\", "/"), emb))
    return refs


def _reference_embedding(path, ext, analysis_args):
    if ext == ".npy":
        emb = np.load(path, allow_pickle=False).astype(np.float32).reshape(-1)
    else:
        with Image.open(path) as im:
            img = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
        faces = _analyze_array(img, *analysis_args, 0)
        if not faces:
            print(f"[ComfyUI-API-DockerCPU] FaceSimilarity: no face found in reference {path}, skipped")
            return None
        largest = max(faces, key=lambda f: f["bbox"]["width"] * f["bbox"]["height"])
        emb = largest["embedding"]
    return emb / max(np.linalg.norm(emb), 1e-12)


class FaceSimilarity:
    """
    Compare one detected face against references by cosine similarity.

    References come from reference_analysis (all its faces) and/or
    reference_folder (images, using their largest face, and .npy embeddings).

    Outputs:
        best_score:  Highest cosine similarity (FLOAT, -1..1; same person is typically > ~0.4)
        best_match:  Label of the best reference (STRING)
        ranking:     JSON list of {label, source, score}, best first (STRING)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "face_analysis": ("FACE_ANALYSIS",),
                "face_index": ("INT", {"default": 0, "min": 0, "max": 4096, "tooltip": "Which face (0-based), counting across frames in FaceAnalyze's sort order. faces_json index 1 = face_index 0."}),
            },
            "optional": {
                "reference_analysis": ("FACE_ANALYSIS",),
                "reference_folder": ("STRING", {"default": "", "tooltip": "Absolute folder of reference images and/or .npy embeddings. Subfolder names become labels."}),
                "provider": (PROVIDER_OPTIONS, {"default": "auto", "tooltip": "Used when embedding reference images."}),
            },
        }

    RETURN_TYPES = ("FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("best_score", "best_match", "ranking")
    FUNCTION = "compare"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Cosine similarity between a detected face and reference faces (FACE_ANALYSIS or a folder of images/.npy embeddings)."

    def compare(self, face_analysis, face_index=0, reference_analysis=None, reference_folder="", provider="auto"):
        faces = [f for frame in face_analysis["frames"] for f in frame]
        if face_index >= len(faces):
            raise ValueError(f"face_index {face_index} out of range: {len(faces)} face(s) detected")
        query = faces[face_index]["embedding"]

        refs = []
        if reference_analysis is not None:
            for fi, frame in enumerate(reference_analysis["frames"]):
                for i, f in enumerate(frame):
                    refs.append((f"frame{fi}_face{i}", "reference_analysis", f["embedding"]))
        if reference_folder and reference_folder.strip():
            # Reference images are embedded with the same models as the query.
            analysis_args = (face_analysis["detector"], face_analysis["recognizer"], provider, 640, 0.5, 0.4)
            refs.extend(_load_reference_folder(reference_folder.strip(), analysis_args))
        if not refs:
            raise ValueError("No references: connect reference_analysis or set reference_folder")

        ranking = sorted(
            ({"label": label, "source": source, "score": round(float(np.dot(query, emb)), 4)} for label, source, emb in refs),
            key=lambda r: -r["score"],
        )
        best = ranking[0]
        return (best["score"], best["label"], json.dumps(ranking))


NODE_CLASS_MAPPINGS = {
    "FaceAnalyze": FaceAnalyze,
    "FaceSimilarity": FaceSimilarity,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FaceAnalyze": "Face Analyze (InsightFace ONNX)",
    "FaceSimilarity": "Face Similarity (ArcFace)",
}
