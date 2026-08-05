import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function findWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function setWidgetValue(node, name, value) {
    const w = findWidget(node, name);
    if (w) w.value = value;
}

function hideWidget(node, name) {
    const w = findWidget(node, name);
    if (!w) return;
    w.type = "hidden";
    w.computeSize = () => [0, -4];
}

function setComboValues(widget, values) {
    widget.options = widget.options || {};
    widget.options.values = values;
}

function selectedFilename(node) {
    const w = findWidget(node, "image");
    return w ? w.value : null;
}

function viewUrl(filename) {
    const p = new URLSearchParams();
    p.set("filename", filename);
    p.set("type", "input");
    p.set("subfolder", "");
    return api.apiURL("/view?" + p.toString());
}

function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
}

function stop(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
}

function attachFolderRefresh(node) {
    const folderTypeWidget = findWidget(node, "folder_type");
    const imageWidget = findWidget(node, "image");
    if (!folderTypeWidget || !imageWidget) return;

    const setImageUploadEnabled = (enabled) => {
        imageWidget.options = imageWidget.options || {};
        if (enabled) {
            imageWidget.options.image_upload = true;
        } else {
            delete imageWidget.options.image_upload;
        }
    };

    const refreshFiles = async () => {
        const previous = imageWidget.value;
        const folderType = folderTypeWidget.value || "input";
        const params = new URLSearchParams({ folder_type: folderType });
        setImageUploadEnabled(folderType === "input");
        try {
            const response = await api.fetchApi(`/dockercpu/load_image_with_metadata/files?${params.toString()}`);
            if (!response.ok) {
                throw new Error(await response.text());
            }
            const payload = await response.json();
            const files = Array.isArray(payload.files) ? payload.files : [];
            setComboValues(imageWidget, files);
            imageWidget.value = files.includes(previous) ? previous : (files[0] || "");
        } catch (error) {
            console.error("LoadImageWithMetadataCrop file refresh failed", error);
        }
        node.setDirtyCanvas(true, true);
    };

    setImageUploadEnabled((folderTypeWidget.value || "input") === "input");

    const callback = folderTypeWidget.callback;
    folderTypeWidget.callback = function () {
        const value = callback?.apply(this, arguments);
        refreshFiles();
        return value;
    };
}

function attachCropEditor(node) {
    hideWidget(node, "crop_x");
    hideWidget(node, "crop_y");
    hideWidget(node, "crop_width");
    hideWidget(node, "crop_height");

    node._limc_img = new Image();
    node._limc_imgLoaded = false;
    node._limc_filename = null;
    node._limc_crop = null;
    node._limc_imageRect = null;
    node._limc_dragging = false;
    node._limc_action = null;
    node._limc_startPointer = null;
    node._limc_startCrop = null;
    node._limc_handleSizeCss = 8;

    node.addWidget("button", "update canvas", null, () => {
        node._limc_filename = null;
        node._limc_load();
    });

    node.addWidget("button", "reset crop", null, () => {
        node._limc_makeFullCrop();
        node._limc_syncWidgets();
        node._limc_draw();
    });

    const container = document.createElement("div");
    container.style.width = "100%";
    container.style.height = "540px";
    container.style.position = "relative";
    container.style.background = "#111";
    container.style.border = "1px solid #777";
    container.style.borderRadius = "6px";
    container.style.overflow = "hidden";
    container.style.boxSizing = "border-box";
    container.style.userSelect = "none";
    container.style.pointerEvents = "auto";
    container.style.touchAction = "none";

    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    canvas.style.cursor = "crosshair";
    canvas.style.pointerEvents = "auto";
    canvas.style.touchAction = "none";

    const label = document.createElement("div");
    label.style.position = "absolute";
    label.style.left = "8px";
    label.style.bottom = "6px";
    label.style.padding = "3px 6px";
    label.style.borderRadius = "4px";
    label.style.background = "rgba(0,0,0,0.70)";
    label.style.color = "white";
    label.style.font = "13px sans-serif";
    label.style.pointerEvents = "none";
    label.textContent = "load image";

    container.appendChild(canvas);
    container.appendChild(label);

    node._limc_container = container;
    node._limc_canvas = canvas;
    node._limc_label = label;
    node._limc_ctx = canvas.getContext("2d");

    const domWidget = node.addDOMWidget("crop_editor", "div", container, {
        serialize: false,
        hideOnZoom: false,
    });

    domWidget.computeSize = (width) => {
        const h = Math.max(360, Math.min(900, node.size[1] - 150));
        container.style.height = `${h}px`;
        return [width, h];
    };

    const resizeObserver = new ResizeObserver(() => node._limc_draw());
    resizeObserver.observe(container);

    node._limc_imgSize = () => ({
        w: node._limc_img.naturalWidth || node._limc_img.width || 1,
        h: node._limc_img.naturalHeight || node._limc_img.height || 1,
    });

    node._limc_canvasCssSize = () => {
        const rect = canvas.getBoundingClientRect();
        return { w: Math.max(1, rect.width), h: Math.max(1, rect.height) };
    };

    node._limc_updateCanvasBackingStore = () => {
        const { w, h } = node._limc_canvasCssSize();
        const dpr = window.devicePixelRatio || 1;
        const bw = Math.max(1, Math.round(w * dpr));
        const bh = Math.max(1, Math.round(h * dpr));
        const resized = canvas.width !== bw || canvas.height !== bh;
        if (resized) {
            canvas.width = bw;
            canvas.height = bh;
        }
        const ctx = node._limc_ctx;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { cssW: w, cssH: h, dpr, resized };
    };

    node._limc_computeImageRect = (cssW = null, cssH = null) => {
        if (cssW == null || cssH == null) {
            const size = node._limc_canvasCssSize();
            cssW = size.w;
            cssH = size.h;
        }
        if (!node._limc_imgLoaded) {
            node._limc_imageRect = null;
            return null;
        }
        const s = node._limc_imgSize();
        const scale = Math.min(cssW / s.w, cssH / s.h);
        const w = s.w * scale;
        const h = s.h * scale;
        const x = (cssW - w) / 2;
        const y = (cssH - h) / 2;
        node._limc_imageRect = { x, y, w, h, scale, cssW, cssH };
        return node._limc_imageRect;
    };

    node._limc_makeFullCrop = () => {
        if (!node._limc_imgLoaded) {
            node._limc_crop = null;
            return;
        }
        const s = node._limc_imgSize();
        const cropW = Math.round(s.w * 0.25);
        const cropH = Math.round(s.h * 0.25);
        const cropX = Math.round((s.w - cropW) / 4);
        const cropY = Math.round((s.h - cropH) / 4);
        node._limc_crop = { x: cropX, y: cropY, w: cropW, h: cropH };
    };

    node._limc_clampCrop = (crop) => {
        const s = node._limc_imgSize();
        let x = Math.round(crop.x);
        let y = Math.round(crop.y);
        let w = Math.round(crop.w);
        let h = Math.round(crop.h);
        w = clamp(w, 1, s.w);
        h = clamp(h, 1, s.h);
        x = clamp(x, 0, s.w - w);
        y = clamp(y, 0, s.h - h);
        return { x, y, w, h };
    };

    node._limc_syncWidgets = () => {
        if (!node._limc_crop) {
            setWidgetValue(node, "crop_x", -1);
            setWidgetValue(node, "crop_y", -1);
            setWidgetValue(node, "crop_width", -1);
            setWidgetValue(node, "crop_height", -1);
            return;
        }
        node._limc_crop = node._limc_clampCrop(node._limc_crop);
        setWidgetValue(node, "crop_x", node._limc_crop.x);
        setWidgetValue(node, "crop_y", node._limc_crop.y);
        setWidgetValue(node, "crop_width", node._limc_crop.w);
        setWidgetValue(node, "crop_height", node._limc_crop.h);
    };

    node._limc_eventToCssCanvasPoint = (event) => {
        const rect = canvas.getBoundingClientRect();
        return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };

    node._limc_cssPointToImagePixel = (point) => {
        const rct = node._limc_imageRect || node._limc_computeImageRect();
        if (!rct) return null;
        const s = node._limc_imgSize();
        return {
            x: clamp(Math.round((point.x - rct.x) / rct.scale), 0, s.w),
            y: clamp(Math.round((point.y - rct.y) / rct.scale), 0, s.h),
        };
    };

    node._limc_cropToCssRect = () => {
        const rct = node._limc_imageRect || node._limc_computeImageRect();
        if (!rct || !node._limc_crop) return null;
        const c = node._limc_crop;
        return { x: rct.x + c.x * rct.scale, y: rct.y + c.y * rct.scale, w: c.w * rct.scale, h: c.h * rct.scale };
    };

    node._limc_hitTest = (event) => {
        const cr = node._limc_cropToCssRect();
        if (!cr) return "new";
        const p = node._limc_eventToCssCanvasPoint(event);
        const hs = node._limc_handleSizeCss;
        const handles = [
            ["nw", cr.x, cr.y],
            ["n", cr.x + cr.w / 2, cr.y],
            ["ne", cr.x + cr.w, cr.y],
            ["e", cr.x + cr.w, cr.y + cr.h / 2],
            ["se", cr.x + cr.w, cr.y + cr.h],
            ["s", cr.x + cr.w / 2, cr.y + cr.h],
            ["sw", cr.x, cr.y + cr.h],
            ["w", cr.x, cr.y + cr.h / 2],
        ];
        for (const [name, hx, hy] of handles) {
            if (Math.abs(p.x - hx) <= hs && Math.abs(p.y - hy) <= hs) return name;
        }
        if (p.x >= cr.x && p.x <= cr.x + cr.w && p.y >= cr.y && p.y <= cr.y + cr.h) {
            return "move";
        }
        return "new";
    };

    node._limc_cursorForHit = (hit) => ({
        nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize",
        n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize",
        move: "move", new: "crosshair",
    }[hit] || "crosshair");

    node._limc_applyDrag = (event) => {
        const cssPoint = node._limc_eventToCssCanvasPoint(event);
        const imgPoint = node._limc_cssPointToImagePixel(cssPoint);
        if (!imgPoint || !node._limc_startPointer || !node._limc_startCrop) return;
        const s = node._limc_imgSize();
        const dx = imgPoint.x - node._limc_startPointer.x;
        const dy = imgPoint.y - node._limc_startPointer.y;
        const c0 = node._limc_startCrop;
        let x = c0.x, y = c0.y, w = c0.w, h = c0.h;
        if (node._limc_action === "move") {
            x = c0.x + dx;
            y = c0.y + dy;
        } else if (node._limc_action === "new") {
            x = Math.min(node._limc_startPointer.x, imgPoint.x);
            y = Math.min(node._limc_startPointer.y, imgPoint.y);
            w = Math.max(1, Math.abs(imgPoint.x - node._limc_startPointer.x));
            h = Math.max(1, Math.abs(imgPoint.y - node._limc_startPointer.y));
        } else {
            let left = c0.x, top = c0.y, right = c0.x + c0.w, bottom = c0.y + c0.h;
            if (node._limc_action.includes("w")) left = clamp(c0.x + dx, 0, right - 1);
            if (node._limc_action.includes("e")) right = clamp(c0.x + c0.w + dx, left + 1, s.w);
            if (node._limc_action.includes("n")) top = clamp(c0.y + dy, 0, bottom - 1);
            if (node._limc_action.includes("s")) bottom = clamp(c0.y + c0.h + dy, top + 1, s.h);
            x = left; y = top; w = right - left; h = bottom - top;
        }
        node._limc_crop = node._limc_clampCrop({ x, y, w, h });
        node._limc_syncWidgets();
        node._limc_draw();
    };

    canvas.addEventListener("pointerdown", (e) => {
        if (e.button !== 0 || e.isPrimary === false) return;
        stop(e);
        node._limc_load();
        if (!node._limc_imgLoaded) return;
        node._limc_computeImageRect();
        const cssPoint = node._limc_eventToCssCanvasPoint(e);
        const imgPoint = node._limc_cssPointToImagePixel(cssPoint);
        if (!imgPoint) return;
        canvas.setPointerCapture?.(e.pointerId);
        node._limc_action = node._limc_hitTest(e);
        node._limc_startPointer = { x: imgPoint.x, y: imgPoint.y };
        node._limc_startCrop = node._limc_crop ? { ...node._limc_crop } : { x: imgPoint.x, y: imgPoint.y, w: 1, h: 1 };
        if (node._limc_action === "new") {
            node._limc_crop = { x: imgPoint.x, y: imgPoint.y, w: 1, h: 1 };
            node._limc_startCrop = { ...node._limc_crop };
            node._limc_syncWidgets();
            node._limc_draw();
        }
        node._limc_dragging = true;
    }, { capture: true });

    canvas.addEventListener("pointermove", (e) => {
        if (node._limc_dragging) {
            stop(e);
            node._limc_applyDrag(e);
            return;
        }
        if (node._limc_imgLoaded) {
            node._limc_computeImageRect();
            const hit = node._limc_hitTest(e);
            canvas.style.cursor = node._limc_cursorForHit(hit);
        }
    }, { capture: true });

    canvas.addEventListener("pointerup", (e) => {
        if (!node._limc_dragging) return;
        stop(e);
        node._limc_applyDrag(e);
        node._limc_dragging = false;
        node._limc_action = null;
        node._limc_startPointer = null;
        node._limc_startCrop = null;
        canvas.releasePointerCapture?.(e.pointerId);
    }, { capture: true });

    canvas.addEventListener("pointercancel", (e) => {
        if (!node._limc_dragging) return;
        stop(e);
        node._limc_dragging = false;
        node._limc_action = null;
        node._limc_startPointer = null;
        node._limc_startCrop = null;
    }, { capture: true });

    for (const eventName of ["mousedown", "mouseup", "click", "dblclick", "dragstart"]) {
        container.addEventListener(eventName, (e) => {
            if (e.button === 0) stop(e);
        }, { capture: true });
    }
    container.addEventListener("mousemove", (e) => {
        if (node._limc_dragging) stop(e);
    }, { capture: true });

    node._limc_load = () => {
        const fn = selectedFilename(node);
        if (!fn || fn === node._limc_filename) return;

        const cx = findWidget(node, "crop_x")?.value;
        const cy = findWidget(node, "crop_y")?.value;
        const cw = findWidget(node, "crop_width")?.value;
        const ch = findWidget(node, "crop_height")?.value;
        const hasStoredCrop = Number.isInteger(cx) && Number.isInteger(cy) &&
                              Number.isInteger(cw) && Number.isInteger(ch) &&
                              cx >= 0 && cy >= 0 && cw > 0 && ch > 0;
        const previousCrop = hasStoredCrop ? { x: cx, y: cy, w: cw, h: ch } : null;
        const hadPreviousCrop = !!previousCrop;

        node._limc_filename = fn;
        node._limc_imgLoaded = false;
        node._limc_imageRect = null;

        node._limc_img = new Image();
        node._limc_img.onload = () => {
            node._limc_imgLoaded = true;
            if (hadPreviousCrop) {
                node._limc_crop = node._limc_clampCrop(previousCrop);
            } else {
                node._limc_makeFullCrop();
            }
            node._limc_syncWidgets();
            node._limc_draw();
        };
        node._limc_img.onerror = () => {
            node._limc_imgLoaded = false;
            node._limc_draw();
        };
        node._limc_img.src = viewUrl(fn) + "&t=" + Date.now();
        node._limc_draw();
    };

    node._limc_draw = () => {
        const { cssW, cssH } = node._limc_updateCanvasBackingStore();
        const ctx = node._limc_ctx;
        ctx.clearRect(0, 0, cssW, cssH);
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, cssW, cssH);
        if (!node._limc_imgLoaded) {
            node._limc_label.textContent = "load image, then update canvas";
            ctx.fillStyle = "#aaa";
            ctx.font = "16px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("load image, then update canvas", cssW / 2, cssH / 2);
            return;
        }
        const rct = node._limc_computeImageRect(cssW, cssH);
        const s = node._limc_imgSize();
        ctx.drawImage(node._limc_img, rct.x, rct.y, rct.w, rct.h);
        const cr = node._limc_cropToCssRect();
        if (cr && node._limc_crop) {
            ctx.fillStyle = "rgba(0,0,0,0.45)";
            ctx.fillRect(rct.x, rct.y, rct.w, cr.y - rct.y);
            ctx.fillRect(rct.x, cr.y + cr.h, rct.w, rct.y + rct.h - (cr.y + cr.h));
            ctx.fillRect(rct.x, cr.y, cr.x - rct.x, cr.h);
            ctx.fillRect(cr.x + cr.w, cr.y, rct.x + rct.w - (cr.x + cr.w), cr.h);
            ctx.strokeStyle = "white";
            ctx.lineWidth = 3;
            ctx.strokeRect(cr.x, cr.y, cr.w, cr.h);
            ctx.strokeStyle = "black";
            ctx.lineWidth = 1;
            ctx.strokeRect(cr.x + 2, cr.y + 2, Math.max(1, cr.w - 4), Math.max(1, cr.h - 4));
            ctx.strokeStyle = "rgba(255,255,255,0.55)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cr.x + cr.w / 3, cr.y);
            ctx.lineTo(cr.x + cr.w / 3, cr.y + cr.h);
            ctx.moveTo(cr.x + (2 * cr.w) / 3, cr.y);
            ctx.lineTo(cr.x + (2 * cr.w) / 3, cr.y + cr.h);
            ctx.moveTo(cr.x, cr.y + cr.h / 3);
            ctx.lineTo(cr.x + cr.w, cr.y + cr.h / 3);
            ctx.moveTo(cr.x, cr.y + (2 * cr.h) / 3);
            ctx.lineTo(cr.x + cr.w, cr.y + (2 * cr.h) / 3);
            ctx.stroke();
            const hs = node._limc_handleSizeCss;
            const handles = [
                [cr.x, cr.y], [cr.x + cr.w / 2, cr.y], [cr.x + cr.w, cr.y],
                [cr.x + cr.w, cr.y + cr.h / 2], [cr.x + cr.w, cr.y + cr.h],
                [cr.x + cr.w / 2, cr.y + cr.h], [cr.x, cr.y + cr.h],
                [cr.x, cr.y + cr.h / 2],
            ];
            for (const [hx, hy] of handles) {
                ctx.fillStyle = "lightblue";
                ctx.fillRect(hx - hs / 2, hy - hs / 2, hs, hs);
                ctx.strokeStyle = "black";
                ctx.lineWidth = 1;
                ctx.strokeRect(hx - hs / 2, hy - hs / 2, hs, hs);
            }
            const c = node._limc_crop;
            const fullDiagonal = Math.hypot(s.w, s.h);
            const cropDiagonal = Math.max(1e-9, Math.hypot(c.w, c.h));
            const zoom = fullDiagonal / cropDiagonal;
            node._limc_label.textContent = `crop ${c.w} \u00d7 ${c.h} \u2014 zoom ${zoom.toFixed(3)}x`;
        } else {
            node._limc_label.textContent = `${s.w} \u00d7 ${s.h}`;
        }
    };

    const imageWidget = findWidget(node, "image");
    if (imageWidget) {
        const oldCallback = imageWidget.callback;
        imageWidget.callback = (...args) => {
            oldCallback?.apply(imageWidget, args);
            node._limc_filename = null;
            setTimeout(() => node._limc_load(), 50);
        };
    }

    setTimeout(() => node._limc_load(), 250);
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.LoadImageWithMetadataCrop",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LoadImageWithMetadataCrop") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            this.size = [900, 720];
            this.serialize_widgets = true;
            attachFolderRefresh(this);
            attachCropEditor(this);
            return result;
        };
    },
});
