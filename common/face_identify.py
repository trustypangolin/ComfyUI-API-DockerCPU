"""
Face identification for ComfyUI-API-DockerCPU (numpy + PIL + onnxruntime).

- FaceIdentify:          Every face in one image vs reference folders (subfolder = label).
                         List outputs, one per face, ready for SaveImageWithFilename.
- FaceCluster:           Groups faces across a folder (average-linkage, cosine) to
                         bootstrap reference sets.
- CollectLabelledFaces:  Reads a folder-based review (crops moved between label
                         folders) back into a CSV, and optionally refreshes references.

Crops are square (bbox x crop_pad), centred, clamped to the image, at native
resolution. Face numbering (_pNN) follows FaceAnalyze's order (left_to_right).
"""

import csv
import io
import json
import os
import shutil

import numpy as np
from PIL import Image

import folder_paths

from .face_analysis import PROVIDER_OPTIONS, _load_reference_folder, resolve_reference_folder
from .output_paths import IF_EXISTS_OPTIONS, clean_relative_dir, stage_output_path, write_atomic

AGGREGATE_OPTIONS = ["max", "mean_top3"]
CLUSTERS_DIR = "_clusters"


def face_suffix(index):
    """_p01, _p02, ... for a 0-based face index."""
    return f"_p{index + 1:02d}"


def square_crop_box(bbox, pad, width, height):
    """Square box of side max(w, h) * pad centred on bbox, shifted to stay inside
    the image and shrunk only when larger than the image. Integer pixels."""
    side = max(bbox["width"], bbox["height"]) * pad
    side = int(round(min(side, width, height)))
    side = max(1, side)
    cx = bbox["x"] + bbox["width"] / 2
    cy = bbox["y"] + bbox["height"] / 2
    x = int(round(min(max(cx - side / 2, 0), width - side)))
    y = int(round(min(max(cy - side / 2, 0), height - side)))
    return {"x": x, "y": y, "width": side, "height": side}


def crop_image(frame, box):
    """IMAGE crop (1xHxWxC) of a single frame tensor (HxWxC)."""
    return frame[box["y"]:box["y"] + box["height"], box["x"]:box["x"] + box["width"], :].unsqueeze(0)


def _round_box(b):
    return {k: round(float(b[k]), 1) for k in ("x", "y", "width", "height")}


def crop_keypoints(face, box):
    """Face keypoints relative to a crop box, for the crop's 'restore' metadata,
    so the crop can later serve as a reference without re-detection."""
    return [[round(float(x) - box["x"], 2), round(float(y) - box["y"], 2)] for x, y in face["kps"]]


def _aggregate(scores, mode):
    scores = sorted(scores, reverse=True)
    if mode == "mean_top3":
        return float(np.mean(scores[:3]))
    return float(scores[0])


def identify_faces(faces, refs, threshold, margin, aggregate, unknown_label):
    """Decide a label for each face from reference embeddings.

    refs: list of (label, source, embedding). Each label's scores are combined
    with `aggregate`; the best label wins if it clears `threshold` and beats the
    best *different* label by `margin`.
    """
    labels = sorted({r[0] for r in refs})
    ref_emb = np.stack([r[2] for r in refs]) if refs else np.zeros((0, 512), np.float32)
    ref_label = np.array([r[0] for r in refs])
    results = []
    for f in faces:
        sims = ref_emb @ f["embedding"] if len(refs) else np.zeros(0)
        per_label = sorted(((_aggregate(sims[ref_label == lab], aggregate), lab) for lab in labels), reverse=True)
        best_score, best = per_label[0] if per_label else (0.0, "")
        runner_score, runner = per_label[1] if len(per_label) > 1 else (0.0, "")
        if best_score < threshold:
            decided_by = "below_threshold"
        elif runner and best_score - runner_score < margin:
            decided_by = "low_margin"
        else:
            decided_by = "match"
        results.append({
            "label": best if decided_by == "match" else unknown_label,
            "best": best, "score": round(best_score, 4),
            "runner_up": runner, "runner_up_score": round(runner_score, 4),
            "decided_by": decided_by,
        })
    return results


class FaceIdentify:
    """
    Identify every face in one image against a reference folder
    (<folder>/<Label>/*.png|*.jpg|*.npy).

    List outputs, one entry per face in FaceAnalyze order:
        face_crop, label, score, runner_up, runner_up_score, suffix (_pNN),
        subfolder (= label), crop_box_json, restore_json (for SaveImageWithFilename.extra_metadata)
    Non-list output:
        summary_json: [{index, bbox, crop_box, label, best, score, runner_up, runner_up_score, decided_by}]
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "face_analysis": ("FACE_ANALYSIS",),
                "reference_folder": ("STRING", {"default": "dataset/_references", "tooltip": "Relative to the input folder, or absolute. Subfolder name = label."}),
                "threshold": ("FLOAT", {"default": 0.40, "min": -1.0, "max": 1.0, "step": 0.01, "tooltip": "Minimum best score to assign a label."}),
                "margin": ("FLOAT", {"default": 0.05, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "Best minus runner-up (a different label) must reach this."}),
                "aggregate": (AGGREGATE_OPTIONS, {"default": "max", "tooltip": "How one label's reference scores combine."}),
                "unknown_label": ("STRING", {"default": "unknown"}),
                "crop_pad": ("FLOAT", {"default": 1.6, "min": 1.0, "max": 8.0, "step": 0.05, "tooltip": "Square crop side = max(bbox w, h) x crop_pad, native resolution."}),
                "provider": (PROVIDER_OPTIONS, {"default": "auto", "tooltip": "Used when embedding reference images."}),
            },
            "optional": {
                "source": ("STRING", {"forceInput": True, "tooltip": "Source image path for restore_json, e.g. REL_DIR/BASE_FILENAME."}),
                "mirror_dir": ("STRING", {"forceInput": True, "tooltip": "This image's MIRROR_DIR, repeated per face so batch saves pair correctly."}),
                "stem": ("STRING", {"forceInput": True, "tooltip": "This image's STEM, repeated per face."}),
                "suffix_extra": ("STRING", {"default": "", "tooltip": "Appended to each suffix, e.g. _head -> _p01_head."}),
            },
        }

    # Outputs after summary_json were appended later (R15); slot order is kept.
    RETURN_TYPES = ("IMAGE", "STRING", "FLOAT", "STRING", "FLOAT", "STRING", "STRING", "STRING", "STRING", "STRING",
                    "STRING", "STRING", "STRING")
    RETURN_NAMES = ("face_crop", "label", "score", "runner_up", "runner_up_score", "suffix", "subfolder",
                    "crop_box_json", "restore_json", "summary_json", "mirror_dir", "stem", "save_dir")
    OUTPUT_IS_LIST = (True,) * 9 + (False,) + (True,) * 3
    FUNCTION = "identify"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Identifies every face in an image against reference folders and returns per-face crops and labels as lists."

    def identify(self, image, face_analysis, reference_folder, threshold=0.40, margin=0.05, aggregate="max",
                 unknown_label="unknown", crop_pad=1.6, provider="auto", source="", mirror_dir="", stem="", suffix_extra=""):
        mirror_dir = (mirror_dir or "").strip().strip("/\\")
        stem = stem or ""
        suffix_extra = suffix_extra or ""
        if image.shape[0] != 1 or len(face_analysis["frames"]) != 1:
            raise ValueError("FaceIdentify takes a single image; feed batches as a list (e.g. from the folder loader)")
        faces = face_analysis["frames"][0]
        frame = image[0]
        H, W = frame.shape[0], frame.shape[1]

        refs = []
        if faces:
            analysis_args = (face_analysis["detector"], face_analysis["recognizer"], provider, 640, 0.5, 0.4)
            refs = _load_reference_folder(resolve_reference_folder(reference_folder), analysis_args)
            if not refs:
                raise ValueError(f"No usable references in {reference_folder!r}")
        decisions = identify_faces(faces, refs, threshold, margin, aggregate, unknown_label)

        out = tuple([] for _ in range(9))
        passthrough = tuple([] for _ in range(3))
        summary = []
        for i, (f, d) in enumerate(zip(faces, decisions)):
            box = square_crop_box(f["bbox"], crop_pad, W, H)
            entry = {"index": i + 1, "bbox": _round_box(f["bbox"]), "crop_box": box, **d}
            summary.append(entry)
            restore = {"node": "FaceIdentify", "source": source or "", "original_label": d["label"],
                       **{k: entry[k] for k in ("index", "bbox", "crop_box", "score", "runner_up", "runner_up_score", "decided_by")},
                       "kps": crop_keypoints(f, box)}
            values = (crop_image(frame, box), d["label"], d["score"], d["runner_up"], d["runner_up_score"],
                      face_suffix(i) + suffix_extra, d["label"], json.dumps(box), json.dumps(restore))
            for lst, v in zip(out, values):
                lst.append(v)
            save_dir = f"{d['label']}/{mirror_dir}" if mirror_dir else d["label"]
            for lst, v in zip(passthrough, (mirror_dir, stem, save_dir)):
                lst.append(v)
        return out + (json.dumps(summary),) + passthrough


# ---------------------------------------------------------------- clustering

def average_linkage(emb, distance_threshold):
    """Agglomerative clustering (average linkage, cosine distance) of L2-normalised
    embeddings. Merges while the closest pair of clusters is within
    distance_threshold. Returns a cluster id per row."""
    n = len(emb)
    if n == 0:
        return np.zeros(0, int)
    dist = (1.0 - emb @ emb.T).astype(np.float64)
    np.fill_diagonal(dist, np.inf)
    sizes = np.ones(n)
    active = np.ones(n, bool)
    members = {i: [i] for i in range(n)}
    while active.sum() > 1:
        idx = np.flatnonzero(active)
        sub = dist[np.ix_(idx, idx)]
        flat = int(np.argmin(sub))
        a, b = idx[flat // len(idx)], idx[flat % len(idx)]
        if sub.flat[flat] > distance_threshold:
            break
        # Lance-Williams update for average linkage: merge b into a.
        dist[a, :] = (sizes[a] * dist[a, :] + sizes[b] * dist[b, :]) / (sizes[a] + sizes[b])
        dist[:, a] = dist[a, :]
        dist[a, a] = np.inf
        dist[b, :] = dist[:, b] = np.inf
        sizes[a] += sizes[b]
        active[b] = False
        members[a] += members.pop(b)
    labels = np.empty(n, int)
    for cid, rows in enumerate(members.values()):
        labels[rows] = cid
    return labels


class FaceCluster:
    """
    Cluster faces across a folder by ArcFace embedding (average linkage,
    cosine distance). Batch node: takes the lists from LoadImagesFromFolderWithMetadata
    and FaceAnalyze run on each list item.

    Clusters are numbered by size (cluster_01 = largest); clusters smaller than
    min_cluster_size are labelled 'singles'.

    List outputs, one entry per face: face_crop, cluster, mirror_dir, stem,
    suffix (_pNN), crop_box_json, restore_json. Non-list: summary_json.
    """

    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "face_analysis": ("FACE_ANALYSIS",),
                "stems": ("STRING", {"forceInput": True}),
                "mirror_dirs": ("STRING", {"forceInput": True}),
                "distance_threshold": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "Cosine distance (1 - similarity) up to which clusters merge."}),
                "min_cluster_size": ("INT", {"default": 2, "min": 1, "max": 1000}),
                "crop_pad": ("FLOAT", {"default": 1.6, "min": 1.0, "max": 8.0, "step": 0.05}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("face_crop", "cluster", "mirror_dir", "stem", "suffix", "crop_box_json", "restore_json", "summary_json")
    OUTPUT_IS_LIST = (True,) * 7 + (False,)
    FUNCTION = "cluster"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Groups faces across a folder by embedding (average-linkage clustering) to bootstrap reference sets."

    def cluster(self, images, face_analysis, stems, mirror_dirs, distance_threshold, min_cluster_size, crop_pad):
        distance_threshold, min_cluster_size, crop_pad = distance_threshold[0], min_cluster_size[0], crop_pad[0]
        if not (len(images) == len(face_analysis) == len(stems) == len(mirror_dirs)):
            raise ValueError(f"List lengths differ: images {len(images)}, face_analysis {len(face_analysis)}, "
                             f"stems {len(stems)}, mirror_dirs {len(mirror_dirs)}")

        faces = []  # (image index, face index, face)
        for ii, fa in enumerate(face_analysis):
            if len(fa["frames"]) != 1:
                raise ValueError("FaceCluster expects one frame per list item")
            faces += [(ii, fi, f) for fi, f in enumerate(fa["frames"][0])]

        emb = np.stack([f["embedding"] for _, _, f in faces]) if faces else np.zeros((0, 512), np.float32)
        raw = average_linkage(emb, distance_threshold)

        # Name clusters by size (largest first, then first appearance); small ones -> singles.
        order = sorted(set(raw.tolist()), key=lambda c: (-int((raw == c).sum()), int(np.flatnonzero(raw == c)[0])))
        names, n = {}, 0
        for c in order:
            if (raw == c).sum() >= min_cluster_size:
                n += 1
                names[c] = f"cluster_{n:02d}"
            else:
                names[c] = "singles"
        width = max(2, len(str(n)))
        names = {c: (f"cluster_{int(v[8:]):0{width}d}" if v != "singles" else v) for c, v in names.items()}

        out = tuple([] for _ in range(7))
        summary = {"distance_threshold": distance_threshold, "faces": len(faces), "clusters": {}, "singles": []}
        for row, (ii, fi, f) in enumerate(faces):
            frame = images[ii][0]
            box = square_crop_box(f["bbox"], crop_pad, frame.shape[1], frame.shape[0])
            name = names[raw[row]]
            member = f"{mirror_dirs[ii]}/{stems[ii]}{face_suffix(fi)}" if mirror_dirs[ii] else f"{stems[ii]}{face_suffix(fi)}"
            restore = {"node": "FaceCluster", "source": f"{mirror_dirs[ii]}/{stems[ii]}".lstrip("/"), "original_label": name,
                       "index": fi + 1, "bbox": _round_box(f["bbox"]), "crop_box": box, "score": round(f["score"], 4),
                       "kps": crop_keypoints(f, box)}
            values = (crop_image(frame, box), name, mirror_dirs[ii], stems[ii], face_suffix(fi), json.dumps(box), json.dumps(restore))
            for lst, v in zip(out, values):
                lst.append(v)
            if name == "singles":
                summary["singles"].append(member)
            else:
                summary["clusters"].setdefault(name, {"members": [], "rows": []})
                summary["clusters"][name]["members"].append(member)
                summary["clusters"][name]["rows"].append(row)

        for name, c in summary["clusters"].items():
            rows = c.pop("rows")
            sims = emb[rows] @ emb[rows].T
            k = len(rows)
            c["size"] = k
            c["mean_similarity"] = round(float((sims.sum() - k) / (k * (k - 1))), 4) if k > 1 else 1.0
        summary["clusters"] = dict(sorted(summary["clusters"].items()))
        return out + (json.dumps(summary),)


# ---------------------------------------------------------------- review collector

CSV_COLUMNS = ["label", "original_label", "changed", "source", "folder", "stem", "index", "bbox", "score", "file"]


def _split_crop_name(filename):
    """'img0001_p02.png' -> ('img0001', 2); index None when there's no _pNN suffix."""
    stem = os.path.splitext(filename)[0]
    base, sep, num = stem.rpartition("_p")
    if sep and num.isdigit():
        return base, int(num)
    return stem, None


def _read_restore(path):
    try:
        with Image.open(path) as im:
            text = im.info.get("restore")
        return json.loads(text) if text else {}
    except (OSError, json.JSONDecodeError):
        return {}


class CollectLabelledFaces:
    """
    Read a folder-based face review back into a CSV.

    Walks output/<review_root>/<Label>/<orig folder>/<stem>_pNN.png (skipping
    _clusters/ and other _-prefixed folders), compares each crop's current
    folder with the label in its PNG 'restore' metadata, and writes
    <review_root>/<csv_name>. Optionally copies confirmed crops into
    input/<references_root>/<Label>/<folder>_<stem>_pNN.png (needs
    allow_input_dir; never under input/originals; skips exclude_list and skip_labels).

    Outputs: csv_path, summary (JSON: counts per label, changed, references copied / excluded / not in review)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "review_root": ("STRING", {"default": "02_identify", "tooltip": "Folder under the output dir holding <Label>/<folder>/ crops."}),
                "csv_name": ("STRING", {"default": "identify.csv"}),
                "if_exists": (IF_EXISTS_OPTIONS, {"default": "overwrite", "tooltip": "For the CSV and reference copies."}),
            },
            "optional": {
                "references_root": ("STRING", {"default": "dataset/_references", "tooltip": "Folder under the input dir for confirmed reference crops."}),
                "update_references": ("BOOLEAN", {"default": False}),
                "allow_input_dir": ("BOOLEAN", {"default": False, "tooltip": "Required for update_references: it writes under the input folder (never originals/)."}),
                "exclude_list": ("STRING", {"default": "", "multiline": True, "tooltip": "One <folder>/<stem> per line (holdouts) that must never become references."}),
                "skip_labels": ("STRING", {"default": "unknown, reject", "tooltip": "Comma-separated labels never copied to references."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("csv_path", "summary")
    FUNCTION = "collect"
    OUTPUT_NODE = True
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Reads face crops sorted into label folders back into a CSV and optionally refreshes reference folders."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")  # the review folders change outside ComfyUI: always re-run

    def collect(self, review_root, csv_name="identify.csv", if_exists="overwrite", references_root="dataset/_references",
                update_references=False, allow_input_dir=False, exclude_list="", skip_labels="unknown, reject"):
        output_dir = folder_paths.get_output_directory()
        review_rel = clean_relative_dir(review_root, "review_root")
        root = os.path.join(output_dir, review_rel)
        if not folder_paths.is_within_directory(output_dir, root) or not os.path.isdir(root):
            raise FileNotFoundError(f"Review folder not found under the output dir: {review_root}")

        rows = []
        for label in sorted(os.listdir(root)):
            label_dir = os.path.join(root, label)
            if not os.path.isdir(label_dir) or label.startswith(("_", ".")):
                continue
            for dirpath, dirs, files in os.walk(label_dir):
                dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
                folder = os.path.relpath(dirpath, label_dir).replace("\\", "/")
                folder = "" if folder == "." else folder
                for name in sorted(files):
                    if not name.lower().endswith(".png"):
                        continue
                    path = os.path.join(dirpath, name)
                    stem, index = _split_crop_name(name)
                    restore = _read_restore(path)
                    original = restore.get("original_label", "")
                    rows.append({
                        "label": label, "original_label": original,
                        "changed": bool(original) and original != label,
                        "source": restore.get("source", ""), "folder": folder, "stem": stem,
                        "index": restore.get("index", index if index is not None else ""),
                        "bbox": json.dumps(restore["bbox"]) if "bbox" in restore else "",
                        "score": restore.get("score", ""),
                        "file": os.path.relpath(path, root).replace("\\", "/"),
                        "_path": path,
                    })

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        csv_path = stage_output_path(review_rel, "", csv_name)

        def write_csv(tmp):
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(buf.getvalue())
        write_atomic(csv_path, write_csv, if_exists)

        counts = {}
        for r in rows:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
        summary = {"faces": len(rows), "per_label": counts, "changed": sum(r["changed"] for r in rows)}

        if update_references:
            summary.update(self._update_references(rows, references_root, allow_input_dir, exclude_list, skip_labels, if_exists))
        return {"ui": {"text": [json.dumps(summary)]}, "result": (csv_path, json.dumps(summary))}

    @staticmethod
    def _update_references(rows, references_root, allow_input_dir, exclude_list, skip_labels, if_exists):
        if not allow_input_dir:
            raise ValueError("update_references writes under the input folder: set allow_input_dir to confirm")
        input_dir = folder_paths.get_input_directory()
        refs_rel = clean_relative_dir(references_root, "references_root")
        if not refs_rel:
            raise ValueError("references_root is empty")
        refs_dir = os.path.abspath(os.path.join(input_dir, refs_rel))
        if not folder_paths.is_within_directory(input_dir, refs_dir):
            raise ValueError(f"references_root resolves outside of the input directory: {refs_dir}")
        if folder_paths.is_within_directory(os.path.join(input_dir, "originals"), refs_dir):
            raise ValueError("references_root must not be under input/originals")

        excluded = {e.strip().replace("\\", "/").strip("/").casefold() for e in exclude_list.splitlines() if e.strip()}
        skip = {s.strip().casefold() for s in skip_labels.split(",") if s.strip()}

        def is_excluded(r):
            key = f"{r['folder']}/{r['stem']}".strip("/").casefold()
            source = os.path.splitext(r["source"].replace("\\", "/"))[0].casefold()
            return key in excluded or any(source == e or source.endswith("/" + e) for e in excluded)

        copied, skipped_excluded, wanted = 0, [], set()
        for r in rows:
            if r["label"].casefold() in skip:
                continue
            if is_excluded(r):
                skipped_excluded.append(r["file"])
                continue
            suffix = f"_p{int(r['index']):02d}" if str(r["index"]).isdigit() else ""
            name = "_".join(p for p in (r["folder"].replace("/", "_"), f"{r['stem']}{suffix}") if p) + ".png"
            dest = os.path.join(refs_dir, r["label"], name)
            wanted.add(os.path.normcase(dest))
            if write_atomic(dest, lambda tmp, src=r["_path"]: shutil.copyfile(src, tmp), if_exists):
                copied += 1

        # Reference files this review doesn't account for: earlier copies whose crop has
        # since moved label, or refs added by hand. Reported, never deleted.
        stale = []
        if os.path.isdir(refs_dir):
            for dirpath, _dirs, files in os.walk(refs_dir):
                for name in files:
                    p = os.path.join(dirpath, name)
                    if name.lower().endswith(".png") and os.path.normcase(p) not in wanted:
                        stale.append(os.path.relpath(p, refs_dir).replace("\\", "/"))
        return {"references_copied": copied, "references_excluded": skipped_excluded, "references_not_in_review": sorted(stale)}


NODE_CLASS_MAPPINGS = {
    "FaceIdentify": FaceIdentify,
    "FaceCluster": FaceCluster,
    "CollectLabelledFaces": CollectLabelledFaces,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FaceIdentify": "Face Identify (ArcFace)",
    "FaceCluster": "Face Cluster (ArcFace)",
    "CollectLabelledFaces": "Collect Labelled Faces",
}
