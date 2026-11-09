import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Bedrock nodes: keep the profile list in sync with ~/.aws/config and load the model list
// live for each node's own profile + region.
const NODES = { BedrockConverse: "text", BedrockInvokeModel: "all" };

function findWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function setComboValues(widget, values) {
    widget.options = widget.options || {};
    widget.options.values = values;
}

async function getJson(url) {
    const response = await api.fetchApi(url);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.Bedrock",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const kind = NODES[nodeData.name];
        if (!kind) {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const profileWidget = findWidget(this, "profile");
            const regionWidget = findWidget(this, "region");
            const modelWidget = findWidget(this, "model");
            let timer = null;
            let generation = 0;

            const refreshProfiles = async () => {
                if (!profileWidget) {
                    return;
                }
                try {
                    const payload = await getJson("/dockercpu/bedrock/profiles");
                    const values = Array.isArray(payload.profiles) ? [...payload.profiles] : [];
                    const current = profileWidget.value;
                    // Keep a saved profile visible even if this machine's config lacks it
                    if (current && !values.includes(current)) {
                        values.push(current);
                    }
                    if (values.length) {
                        setComboValues(profileWidget, values);
                    }
                } catch (error) {
                    console.warn("Bedrock profile refresh failed", error);
                }
            };

            const refreshModels = async (force = false) => {
                if (!modelWidget) {
                    return;
                }
                const mine = ++generation;
                const previous = modelWidget.value;
                const params = new URLSearchParams({
                    profile: profileWidget?.value || "",
                    region: regionWidget?.value || "",
                    kind,
                    refresh: force ? "1" : "0",
                });
                try {
                    const payload = await getJson(`/dockercpu/bedrock/models?${params.toString()}`);
                    if (mine !== generation) {
                        return; // a newer refresh superseded this one
                    }
                    const values = Array.isArray(payload.models) ? [...payload.models] : [];
                    if (previous && !values.includes(previous)) {
                        values.unshift(previous); // never silently swap a saved model
                    }
                    if (values.length) {
                        setComboValues(modelWidget, values);
                        modelWidget.value = previous || values[0];
                    }
                } catch (error) {
                    console.warn(`Bedrock model refresh failed (${params.get("profile")} / ${params.get("region")})`, error);
                }
                this.setDirtyCanvas(true, true);
            };

            const scheduleRefresh = () => {
                clearTimeout(timer);
                timer = setTimeout(() => refreshModels(), 300);
            };

            for (const widget of [profileWidget, regionWidget]) {
                if (!widget) {
                    continue;
                }
                const callback = widget.callback;
                widget.callback = function () {
                    const value = callback?.apply(this, arguments);
                    scheduleRefresh();
                    return value;
                };
            }

            // Saved widget values are applied after onNodeCreated; wait a tick so the refresh
            // uses the workflow's profile/region rather than the defaults.
            setTimeout(() => {
                refreshProfiles();
                refreshModels();
            }, 0);
            return result;
        };

        // Right-click menu: force a fresh model list (e.g. after enabling a model)
        const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function (_, options) {
            const result = getExtraMenuOptions?.apply(this, arguments);
            options.push({
                content: "Refresh Bedrock models",
                callback: async () => {
                    const node = this;
                    const profile = findWidget(node, "profile")?.value || "";
                    const region = findWidget(node, "region")?.value || "";
                    const modelWidget = findWidget(node, "model");
                    try {
                        const params = new URLSearchParams({ profile, region, kind, refresh: "1" });
                        const payload = await getJson(`/dockercpu/bedrock/models?${params.toString()}`);
                        const values = [...(payload.models || [])];
                        if (modelWidget?.value && !values.includes(modelWidget.value)) {
                            values.unshift(modelWidget.value);
                        }
                        if (modelWidget && values.length) {
                            setComboValues(modelWidget, values);
                        }
                        node.setDirtyCanvas(true, true);
                    } catch (error) {
                        alert(`Bedrock model refresh failed:\n${error.message}`);
                    }
                },
            });
            return result;
        };
    },
});
