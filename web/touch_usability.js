import { app } from "../../scripts/app.js";

// ComfyUI's node context menus and combo-widget value lists are both rendered
// via LiteGraph's ContextMenu as `.litemenu-entry` rows inside `.litecontextmenu`.
// Stock sizing is `font-size:12px; padding:0 0 0 2px; margin:2px` (see
// comfyui_frontend_package's bundled CSS) - fine for a mouse pointer, but the
// rows end up only a few CSS pixels tall, which makes selecting a value from a
// dropdown (or any right-click menu) with a finger or Apple Pencil unreliable
// on iPad. `navigator.maxTouchPoints > 0` is true for any iPad regardless of
// whether the pencil or a finger is doing the tapping, and false on
// mouse/trackpad-only desktops, so this only changes behavior on touch devices.
const STYLE_ID = "dockercpu-touch-usability";

function injectTouchStyles() {
    if (document.getElementById(STYLE_ID)) {
        return;
    }
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        .litecontextmenu {
            min-width: 180px !important;
        }
        .litemenu-entry, .litecontextmenu .litemenu-entry {
            padding: 10px 12px !important;
            margin: 2px 4px !important;
            font-size: 16px !important;
            min-height: 20px !important;
            line-height: 1.4 !important;
        }
        .litemenu-entry .property_name,
        .litemenu-entry .property_value {
            min-height: 1.6em !important;
        }
    `;
    document.head.appendChild(style);
}

// LiteGraph's ContextMenu only selects an entry on `click`
// (`element.addEventListener('click', inner_onclick)` in ContextMenu.ts). On
// iPad, a finger tap is turned into a click, but an Apple Pencil tap often is
// not (e.g. when Scribble is enabled, or the precise tip drifts a few pixels),
// so the pencil appears to do nothing. For pen input only, we turn a tap on a
// `.litemenu-entry` into a click ourselves. The synthetic event is a
// MouseEvent carrying the pen's clientX/clientY, which ContextMenu uses to
// position submenus, and any real click Safari sends straight afterwards is
// swallowed so the entry isn't selected twice.
const PEN_TAP_MAX_MOVE_PX = 10; // more movement than this is a scroll/drag, not a tap
const NATIVE_CLICK_SUPPRESS_MS = 500;

function installPenTapClicks() {
    let downX = 0;
    let downY = 0;
    let downEntry = null;
    let suppressNativeClickUntil = 0;

    document.addEventListener(
        "pointerdown",
        (e) => {
            if (e.pointerType !== "pen") {
                return;
            }
            downEntry = e.target instanceof Element ? e.target.closest(".litemenu-entry") : null;
            downX = e.clientX;
            downY = e.clientY;
        },
        true
    );

    document.addEventListener(
        "pointerup",
        (e) => {
            if (e.pointerType !== "pen" || !downEntry) {
                return;
            }
            const entry = e.target instanceof Element ? e.target.closest(".litemenu-entry") : null;
            const moved = Math.hypot(e.clientX - downX, e.clientY - downY);
            const startEntry = downEntry;
            downEntry = null;
            if (entry !== startEntry || moved > PEN_TAP_MAX_MOVE_PX || !entry.isConnected) {
                return;
            }
            suppressNativeClickUntil = performance.now() + NATIVE_CLICK_SUPPRESS_MS;
            entry.dispatchEvent(
                new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    button: 0,
                    clientX: e.clientX,
                    clientY: e.clientY,
                    screenX: e.screenX,
                    screenY: e.screenY,
                })
            );
        },
        true
    );

    document.addEventListener(
        "pointercancel",
        (e) => {
            if (e.pointerType === "pen") {
                downEntry = null;
            }
        },
        true
    );

    // If Safari does deliver its own click after our synthetic one, drop it.
    // The menu has usually closed by then, so the click could otherwise land on
    // whatever is underneath. Only real (isTrusted) clicks are dropped.
    document.addEventListener(
        "click",
        (e) => {
            if (e.isTrusted && performance.now() < suppressNativeClickUntil) {
                suppressNativeClickUntil = 0;
                e.stopImmediatePropagation();
                e.preventDefault();
            }
        },
        true
    );
}

// LiteGraph's CanvasPointer decides click vs drag in `move()`: any pointermove
// arriving more than `CanvasPointer.bufferTime` (default 32ms, setting
// `Comfy.Pointer.ClickBufferTime`) after pointerdown starts a drag, even if
// the pointer hasn't moved. An Apple Pencil held on the glass keeps sending
// pointermove for sub-pixel jitter and pressure changes, so every pencil tap
// becomes a "drag" and `onClick` never runs: widget arrows don't step and
// combo widgets never open their value list. A still finger sends far fewer
// moves, which is why finger taps work. While a pen is down on the graph
// canvas, we hide moves that stay within LiteGraph's click drift (6px,
// `CanvasPointer._maxClickDrift`) from the canvas. Real drags (node moves,
// panning) go past that distance and are passed through unchanged.
const PEN_CANVAS_CLICK_DRIFT_PX = 6;

function installPenCanvasJitterFilter() {
    let pen = null; // { id, x, y, dragging } while a pen is down on the canvas

    const isGraphCanvas = (target) => target != null && target === app.canvas?.canvas;

    document.addEventListener(
        "pointerdown",
        (e) => {
            if (e.pointerType === "pen" && isGraphCanvas(e.target)) {
                pen = { id: e.pointerId, x: e.clientX, y: e.clientY, dragging: false };
            }
        },
        true
    );

    document.addEventListener(
        "pointermove",
        (e) => {
            if (!pen || e.pointerId !== pen.id || pen.dragging) {
                return;
            }
            if (!e.buttons) {
                // Pen lifted without us seeing pointerup; stop filtering.
                pen = null;
                return;
            }
            if (Math.hypot(e.clientX - pen.x, e.clientY - pen.y) > PEN_CANVAS_CLICK_DRIFT_PX) {
                pen.dragging = true; // a real drag: let this and later moves through
                return;
            }
            e.stopImmediatePropagation();
        },
        true
    );

    const endPen = (e) => {
        if (pen && e.pointerId === pen.id) {
            pen = null;
        }
    };
    // Bubble phase on window, so the canvas sees pointerup before we clear state.
    window.addEventListener("pointerup", endPen);
    window.addEventListener("pointercancel", endPen);
}

// Palm rejection: while enabled, every finger touch (pointerType "touch") is
// blocked so a hand can rest on the screen while the pencil does the work.
// Pointer events are stopped at window capture, before LiteGraph or any Vue
// component sees them. touchstart is also cancelled (non-passive listener),
// which stops Safari from turning the touch into mouse events/click, and from
// scrolling or pinch-zooming. The pencil toggle pill is exempt, so a finger can
// always turn palm rejection back off.
//
// Apple Pencil double-tap and squeeze are only delivered to native apps
// (UIKit's UIPencilInteraction); Safari doesn't expose them to web pages, so
// they can't be mapped to anything here.
const SETTING_REJECT_FINGERS = "DockerCPU.Pencil.RejectFingers";
const SETTING_SHOW_PILL = "DockerCPU.Pencil.ShowToggle";
const PILL_ID = "dockercpu-pencil-pill";

const pencilState = {
    rejectFingers: false,
    showPill: true,
    penSeen: false,
};

const isInPill = (target) => target instanceof Element && target.closest(`#${PILL_ID}`) != null;

function installPalmRejection() {
    const blockTouchPointer = (e) => {
        if (pencilState.rejectFingers && e.pointerType === "touch" && !isInPill(e.target)) {
            e.stopImmediatePropagation();
            e.preventDefault();
        }
    };
    for (const type of ["pointerdown", "pointermove", "pointerup", "pointercancel", "pointerover", "pointerenter"]) {
        window.addEventListener(type, blockTouchPointer, { capture: true });
    }

    const blockTouch = (e) => {
        if (pencilState.rejectFingers && !isInPill(e.target)) {
            e.stopImmediatePropagation();
            if (e.cancelable) {
                e.preventDefault();
            }
        }
    };
    for (const type of ["touchstart", "touchmove", "touchend"]) {
        window.addEventListener(type, blockTouch, { capture: true, passive: false });
    }
}

function setSetting(id, value) {
    // [VERIFIED - app.extensionManager is the workspace store (App.vue:22);
    // its setting.set(key, value) wraps settingStore.set (workspaceStore.ts:44)]
    const result = app.extensionManager?.setting?.set(id, value);
    Promise.resolve(result).catch((err) => console.error(`[DockerCPU] Failed to save ${id}:`, err));
}

function updatePill() {
    let pill = document.getElementById(PILL_ID);
    const visible = pencilState.penSeen && pencilState.showPill;
    if (!visible) {
        pill?.remove();
        return;
    }
    if (!pill) {
        pill = document.createElement("button");
        pill.id = PILL_ID;
        pill.type = "button";
        Object.assign(pill.style, {
            position: "fixed",
            right: "16px",
            bottom: "96px",
            zIndex: "10000",
            padding: "8px 14px",
            borderRadius: "999px",
            border: "1px solid rgba(255,255,255,0.25)",
            font: "14px system-ui, sans-serif",
            color: "#fff",
            boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
            touchAction: "manipulation",
            userSelect: "none",
            webkitUserSelect: "none",
        });
        // pointerup rather than click: Safari doesn't always send a click for
        // a pencil tap (see installPenTapClicks).
        let pressed = false;
        pill.addEventListener("pointerdown", () => {
            pressed = true;
        });
        pill.addEventListener("pointerup", (e) => {
            if (!pressed) {
                return;
            }
            pressed = false;
            e.preventDefault();
            pencilState.rejectFingers = !pencilState.rejectFingers;
            setSetting(SETTING_REJECT_FINGERS, pencilState.rejectFingers);
            updatePill();
        });
        pill.addEventListener("pointercancel", () => {
            pressed = false;
        });
        document.body.appendChild(pill);
    }
    pill.textContent = pencilState.rejectFingers ? "✏️ Pencil only" : "✏️ Pencil + finger";
    pill.title = pencilState.rejectFingers
        ? "Finger touches are ignored (palm rejection). Tap to allow fingers again."
        : "Fingers and pencil both work. Tap to ignore finger touches (palm rejection).";
    pill.style.background = pencilState.rejectFingers ? "rgba(37,99,235,0.9)" : "rgba(40,40,40,0.85)";
}

function installPenDetection() {
    window.addEventListener(
        "pointerdown",
        (e) => {
            if (e.pointerType === "pen" && !pencilState.penSeen) {
                pencilState.penSeen = true;
                updatePill();
            }
        },
        { capture: true }
    );
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.TouchUsability",
    // [VERIFIED - extensionService.ts:72 registers `extension.settings`;
    // settingStore.addSetting calls onChange with the current value on
    // registration (settingStore.ts:258), so the state below is loaded at startup]
    settings: [
        {
            id: SETTING_REJECT_FINGERS,
            category: ["DockerCPU", "Pencil", "Ignore finger touches"],
            name: "Ignore finger touches (palm rejection)",
            tooltip:
                "Block all finger input so you can rest your hand on the screen while using an Apple Pencil. Fingers can still tap the pencil toggle to turn this off.",
            type: "boolean",
            defaultValue: false,
            onChange: (value) => {
                pencilState.rejectFingers = value === true;
                updatePill();
            },
        },
        {
            id: SETTING_SHOW_PILL,
            category: ["DockerCPU", "Pencil", "Show pencil toggle"],
            name: "Show pencil toggle when a pencil is used",
            tooltip: "Show a floating button, after the first pencil tap, that switches palm rejection on and off.",
            type: "boolean",
            defaultValue: true,
            onChange: (value) => {
                pencilState.showPill = value !== false;
                updatePill();
            },
        },
    ],
    setup() {
        if (navigator.maxTouchPoints > 0) {
            injectTouchStyles();
            installPenTapClicks();
            installPenCanvasJitterFilter();
            installPalmRejection();
            installPenDetection();
        }
    },
});
