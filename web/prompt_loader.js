import { app } from "../../scripts/app.js";

// Load Prompt From File: show the prompt_file dropdown as folder submenus
// (people/Ben/front.txt -> 📁 people > 📁 Ben > front.txt) at every depth,
// whatever the list length. rgthree's menu auto-nest only nests lists longer
// than its threshold (20), and only one level for short subfolders.
// Classic (LiteGraph) canvas only; the Vue nodes dropdown is unchanged.

const NODE_CLASS = "LoadPromptFromFile";
const WIDGET_NAME = "prompt_file";

const promptWidgets = new Set();

function isPromptList(values) {
    if (!Array.isArray(values) || !values.length || values.some((v) => typeof v !== "string")) return false;
    for (const w of promptWidgets) {
        const own = w.options?.values;
        if (own === values) return true;
        if (Array.isArray(own) && own.length === values.length && own.every((v, i) => v === values[i])) return true;
    }
    return false;
}

function buildTree(paths) {
    const root = { folders: new Map(), files: [] };
    for (const path of paths) {
        const parts = path.split("/");
        let level = root;
        for (const part of parts.slice(0, -1)) {
            if (!level.folders.has(part)) level.folders.set(part, { folders: new Map(), files: [] });
            level = level.folders.get(part);
        }
        level.files.push({ name: parts[parts.length - 1], path });
    }
    return root;
}

// Folders first, then files; both keep the server's alphabetical order.
function toEntries(level, pick) {
    const entries = [];
    for (const [name, sub] of level.folders) {
        entries.push({ content: `📁 ${name}`, has_submenu: true, submenu: { options: toEntries(sub, pick) } });
    }
    for (const file of level.files) {
        entries.push({ content: file.name, title: file.path, callback: () => pick(file.path) });
    }
    return entries;
}

app.registerExtension({
    name: "DockerCPU.PromptLoaderFolders",
    nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;
        const widget = node.widgets?.find((w) => w.name === WIDGET_NAME);
        if (widget) promptWidgets.add(widget);
        const onRemoved = node.onRemoved;
        node.onRemoved = function () {
            promptWidgets.delete(widget);
            return onRemoved?.apply(this, arguments);
        };
    },
    setup() {
        // Deferred so this wrapper sits outside other ContextMenu wrappers
        // (rgthree's auto-nest), which then skip the already-nested entries.
        setTimeout(() => {
            const Original = LiteGraph.ContextMenu;
            function ContextMenu(values, options) {
                if (!options?.parentMenu && options?.callback && isPromptList(values)
                        && values.some((v) => v.includes("/"))) {
                    const callback = options.callback;
                    values = toEntries(buildTree(values), (path) => callback(path));
                    options = { ...options, callback: undefined };
                }
                return new Original(values, options);
            }
            ContextMenu.prototype = Original.prototype;
            Object.setPrototypeOf(ContextMenu, Original);
            LiteGraph.ContextMenu = ContextMenu;
        });
    },
});
