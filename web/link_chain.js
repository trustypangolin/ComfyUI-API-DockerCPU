import { app } from "../../scripts/app.js";

// Link chain highlight: tap (or click) the body of a link to animate the whole
// chain of that type, from where it starts to where it stops. The chain follows
// the link's type through nodes: upstream through each node's inputs of the
// same type, downstream through its outputs of the same type, so
//   Load Image -> Upscale (IMAGE->IMAGE) -> Sharpen (IMAGE->IMAGE) -> VAE Encode (IMAGE->LATENT)
// lights up end to end and stops at VAE Encode. '*' slots (legacy Reroute
// nodes) pass any type through. Tap the same link again, tap empty canvas, or
// press Esc to clear. The link centre dot keeps its stock menu, and Shift/Alt
// drags on a link (move link / add reroute) are untouched.
//
// [VERIFIED - comfyui-frontend-package 1.55.18 bundle, settingStore-*.js]
// - renderLink stores each drawn segment's Path2D on the link (`link.path`),
//   or on the reroute for segments ending at a reroute (`reroute.path`), in
//   graph coordinates; canvas.renderedPaths holds the links/reroutes drawn
//   this frame. queryRenderedLinkSegmentsAtPoint hit-tests the same paths
//   with isPointInStroke and lineWidth connections_width + 7.
// - drawBackCanvas / drawFrontCanvas call `this.drawConnections(ctx, ...)`, so
//   wrapping it on the instance draws the overlay in the links' own layer,
//   above links and below nodes. LGraph.getLink(id) reads graph.links (a Map);
//   LLink.getReroutes(graph, link) is static; Reroute.linkIds is a Set.
// - The stock "recently executed" flow (link._last_time) is not reused: it
//   redraws origin -> target as one curve and ignores reroutes.

const SETTING_ENABLED = "DockerCPU.LinkChain.Enabled";
const TAP_MAX_MOVE_PX = 6; // more movement than this is a pan/drag, not a tap
const HIT_TOLERANCE_PX = 10; // minimum hit width on screen, whatever the zoom

const chain = {
    enabled: true,
    graph: null,
    startIds: [], // the tapped link(s); the chain is recomputed from these every frame
    linkIds: new Set(),
    sources: new Set(),
    sinks: new Set(),
    nodeIds: new Set(),
    color: "#FFF",
    raf: 0,
};

let hitCtx = null;

function typeKeys(type) {
    return String(type ?? "*")
        .toUpperCase()
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
}

function typesMatch(slotType, chainType) {
    const a = typeKeys(slotType);
    const b = typeKeys(chainType);
    return a.includes("*") || b.includes("*") || a.some((t) => b.includes(t));
}

// The concrete type the chain carries: the link's own, or, for a '*' link,
// the type of the slot at either end.
function chainTypeOf(graph, link) {
    if (link.type != null && !typeKeys(link.type).includes("*")) return link.type;
    const origin = graph.getNodeById(link.origin_id)?.outputs?.[link.origin_slot]?.type;
    if (origin != null && !typeKeys(origin).includes("*")) return origin;
    const target = graph.getNodeById(link.target_id)?.inputs?.[link.target_slot]?.type;
    if (target != null && !typeKeys(target).includes("*")) return target;
    return "*";
}

// Pure graph walk: { linkIds, sources, sinks, nodeIds, type } for the chain
// through startIds. Upstream and downstream are walked separately, so sibling
// branches (another consumer of an upstream node's output) are not included.
function collectChain(graph, startIds) {
    const links = startIds.map((id) => graph.getLink(id)).filter(Boolean);
    const linkIds = new Set();
    if (!links.length) return { linkIds, sources: new Set(), sinks: new Set(), nodeIds: new Set(), type: "*" };
    const type = chainTypeOf(graph, links[0]);

    const walk = (stack, next) => {
        const seen = new Set();
        while (stack.length) {
            const id = stack.pop();
            if (seen.has(id)) continue;
            seen.add(id);
            const link = graph.getLink(id);
            if (!link) continue;
            linkIds.add(link.id);
            stack.push(...next(link));
        }
    };
    walk(links.map((l) => l.id), (link) => {
        const node = graph.getNodeById(link.origin_id);
        return (node?.inputs ?? []).filter((i) => i.link != null && typesMatch(i.type, type)).map((i) => i.link);
    });
    walk(links.map((l) => l.id), (link) => {
        const node = graph.getNodeById(link.target_id);
        return (node?.outputs ?? []).filter((o) => typesMatch(o.type, type)).flatMap((o) => o.links ?? []);
    });

    const origins = new Set();
    const targets = new Set();
    for (const id of linkIds) {
        const link = graph.getLink(id);
        origins.add(link.origin_id);
        targets.add(link.target_id);
    }
    const sources = new Set([...origins].filter((n) => !targets.has(n)));
    const sinks = new Set([...targets].filter((n) => !origins.has(n)));
    return { linkIds, sources, sinks, nodeIds: new Set([...origins, ...targets]), type };
}

function linkColor(canvas, graph, type) {
    const colors = canvas.constructor?.link_type_colors ?? {};
    for (const key of [String(type), ...typeKeys(type)]) {
        if (colors[key]) return colors[key];
    }
    return graph.getLink(chain.startIds[0])?.color || canvas.default_link_color || "#FFF";
}

function getHitCtx() {
    if (!hitCtx) {
        const c = typeof OffscreenCanvas !== "undefined" ? new OffscreenCanvas(1, 1) : document.createElement("canvas");
        hitCtx = c.getContext("2d"); // identity transform: paths and point are both graph coordinates
    }
    return hitCtx;
}

// Link ids under a pointer event, from the segments drawn this frame.
function linkIdsAt(canvas, x, y) {
    const ctx = getHitCtx();
    ctx.lineWidth = Math.max((canvas.connections_width ?? 3) + 7, HIT_TOLERANCE_PX / (canvas.ds?.scale || 1));
    for (const seg of canvas.renderedPaths ?? []) {
        if (!(seg.path instanceof Path2D) || !ctx.isPointInStroke(seg.path, x, y)) continue;
        if (seg.linkIds instanceof Set) return [...seg.linkIds]; // reroute: every link through it
        if (seg.origin_id != null) return [seg.id];
    }
    return [];
}

function clearChain() {
    chain.graph = null;
    chain.startIds = [];
    chain.linkIds = new Set();
    chain.nodeIds = new Set();
    if (chain.raf) cancelAnimationFrame(chain.raf);
    chain.raf = 0;
    app.canvas?.setDirty(true, true);
}

function refreshChain(canvas) {
    const graph = canvas.graph;
    if (!graph || graph !== chain.graph || !chain.startIds.some((id) => graph.getLink(id))) {
        clearChain();
        return false;
    }
    // Recomputed each frame so rewiring while the chain is shown stays accurate.
    const found = collectChain(graph, chain.startIds);
    Object.assign(chain, found, { color: linkColor(canvas, graph, found.type) });
    return true;
}

function startChain(canvas, ids) {
    chain.graph = canvas.graph;
    chain.startIds = ids;
    if (!refreshChain(canvas)) return;
    const tick = () => {
        if (!chain.startIds.length) return;
        // Links are drawn on the background canvas unless links_ontop, so both layers redraw.
        app.canvas?.setDirty(true, true);
        chain.raf = requestAnimationFrame(tick);
    };
    if (!chain.raf) chain.raf = requestAnimationFrame(tick);
}

function drawChainLinks(canvas, ctx) {
    if (!chain.startIds.length || !refreshChain(canvas)) return;
    const graph = canvas.graph;
    const drawn = canvas.renderedPaths ?? new Set();
    const paths = new Set();
    for (const id of chain.linkIds) {
        const link = graph.getLink(id);
        if (!link) continue;
        if (link.path instanceof Path2D && drawn.has(link)) paths.add(link.path);
        for (const reroute of link.constructor?.getReroutes?.(graph, link) ?? []) {
            if (reroute.path instanceof Path2D && drawn.has(reroute)) paths.add(reroute.path);
        }
    }
    if (!paths.size) return;

    const t = performance.now() / 1000;
    const width = canvas.connections_width ?? 3;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    // Pulsing glow in the link's own colour.
    ctx.strokeStyle = chain.color;
    ctx.shadowColor = chain.color;
    ctx.shadowBlur = 10 + 8 * Math.sin(t * 4);
    ctx.lineWidth = width + 3;
    for (const p of paths) ctx.stroke(p);
    // White dashes marching from source to destination (paths run origin -> target).
    ctx.shadowBlur = 0;
    ctx.strokeStyle = "#FFF";
    ctx.lineWidth = Math.max(1.5, width * 0.6);
    ctx.setLineDash([10, 16]);
    ctx.lineDashOffset = -((t * 60) % 26);
    for (const p of paths) ctx.stroke(p);
    ctx.restore();
}

function drawChainNodes(canvas, ctx) {
    // Vue nodes are DOM elements, so canvas outlines would not line up with them.
    if (!chain.startIds.length || chain.graph !== canvas.graph || window.LiteGraph?.vueNodesMode) return;
    const t = performance.now() / 1000;
    const pulse = 0.6 + 0.4 * Math.sin(t * 4);
    ctx.save();
    ctx.font = "bold 12px sans-serif";
    ctx.textBaseline = "bottom";
    for (const node of canvas.graph.nodes ?? []) {
        if (!chain.nodeIds.has(node.id)) continue;
        const [x, y, w, h] = node.getBounding();
        const role = chain.sources.has(node.id) ? "SOURCE" : chain.sinks.has(node.id) ? "END" : null;
        ctx.strokeStyle = chain.color;
        ctx.globalAlpha = role ? pulse : 0.6;
        ctx.lineWidth = role ? 3 : 1.5;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x - 4, y - 4, w + 8, h + 8, 8);
        else ctx.rect(x - 4, y - 4, w + 8, h + 8);
        ctx.stroke();
        if (role) {
            ctx.globalAlpha = 1;
            ctx.fillStyle = chain.color;
            ctx.fillText(role, x, y - 8);
        }
    }
    ctx.restore();
}

function onTap(canvas, e) {
    const graph = canvas.graph;
    if (!chain.enabled || !graph) return;
    const [x, y] = canvas.convertEventToCanvasOffset(e);
    if (graph.getNodeOnPos(x, y)) return; // taps on nodes keep the chain shown
    const ids = linkIdsAt(canvas, x, y);
    if (!ids.length) {
        if (chain.startIds.length) clearChain();
        return;
    }
    const same = chain.graph === graph && ids.length === chain.startIds.length && ids.every((id) => chain.startIds.includes(id));
    if (same) clearChain();
    else startChain(canvas, ids);
}

function installPointer(canvas) {
    let down = null;
    const el = canvas.canvas;
    el.addEventListener(
        "pointerdown",
        (e) => {
            const plain = e.button === 0 && !e.shiftKey && !e.altKey && !e.ctrlKey && !e.metaKey;
            down = plain ? { id: e.pointerId, x: e.clientX, y: e.clientY } : null;
        },
        true
    );
    el.addEventListener(
        "pointerup",
        (e) => {
            const start = down;
            down = null;
            if (!start || e.pointerId !== start.id) return;
            if (Math.hypot(e.clientX - start.x, e.clientY - start.y) > TAP_MAX_MOVE_PX) return;
            try {
                onTap(canvas, e);
            } catch (err) {
                console.warn("[DockerCPU] link chain: tap failed", err);
                clearChain();
            }
        },
        true
    );
    el.addEventListener("pointercancel", () => (down = null), true);
}

function installDrawing(canvas) {
    const drawConnections = canvas.drawConnections;
    canvas.drawConnections = function (ctx, ...rest) {
        const result = drawConnections.call(this, ctx, ...rest);
        try {
            drawChainLinks(this, ctx);
        } catch (err) {
            console.warn("[DockerCPU] link chain: draw failed, clearing", err);
            clearChain();
        }
        return result;
    };
    const onDrawForeground = canvas.onDrawForeground;
    canvas.onDrawForeground = function (ctx, area) {
        onDrawForeground?.call(this, ctx, area);
        try {
            drawChainNodes(this, ctx);
        } catch (err) {
            console.warn("[DockerCPU] link chain: draw failed, clearing", err);
            clearChain();
        }
    };
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.LinkChain",
    settings: [
        {
            id: SETTING_ENABLED,
            category: ["DockerCPU", "Links", "Link chain highlight"],
            name: "Tap a link to highlight its whole chain",
            tooltip:
                "Tap or click a link to animate every link of the same type from its source to where it stops (e.g. IMAGE through to VAE Encode). Tap empty canvas or press Esc to clear.",
            type: "boolean",
            defaultValue: true,
            onChange: (value) => {
                chain.enabled = value !== false;
                if (!chain.enabled) clearChain();
            },
        },
    ],
    setup() {
        const canvas = app.canvas;
        if (!canvas?.canvas) {
            console.warn("[DockerCPU] link chain: no canvas, not installed");
            return;
        }
        installDrawing(canvas);
        installPointer(canvas);
        document.addEventListener("keydown", (e) => {
            if (e.key !== "Escape" || !chain.startIds.length) return;
            if (e.target instanceof Element && e.target.closest("input, textarea, [contenteditable]")) return;
            clearChain();
        });
    },
});

// Exposed for tests only.
export { collectChain, typesMatch };
