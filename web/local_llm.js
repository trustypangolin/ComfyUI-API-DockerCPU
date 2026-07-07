import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function findWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function setComboValues(widget, values) {
    widget.options = widget.options || {};
    widget.options.values = values;
}

app.registerExtension({
    name: "ComfyUI-API-DockerCPU.LocalLLM",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LocalLLM") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            const endpointWidget = findWidget(this, "endpoint_url");
            const apiKeyWidget = findWidget(this, "api_key");
            const apiTypeWidget = findWidget(this, "api_type");
            const modelWidget = findWidget(this, "model");
            const timeoutWidget = findWidget(this, "timeout");
            let timer = null;

            const refreshModels = async () => {
                if (!endpointWidget || !modelWidget) {
                    return;
                }

                const previous = modelWidget.value;
                const params = new URLSearchParams({
                    endpoint_url: endpointWidget.value || "http://localhost:1234",
                    api_key: apiKeyWidget?.value || "",
                    api_type: apiTypeWidget?.value || "openai_compatible",
                    timeout: String(timeoutWidget?.value || 10),
                });

                try {
                    const response = await api.fetchApi(`/dockercpu/local_llm/models?${params.toString()}`);
                    if (!response.ok) {
                        throw new Error(await response.text());
                    }
                    const payload = await response.json();
                    const models = Array.isArray(payload.models) ? payload.models : [];
                    const values = models.length ? [...models, "auto"] : ["auto"];
                    if (previous && !values.includes(previous)) {
                        values.push(previous);
                    }
                    setComboValues(modelWidget, values);
                    modelWidget.value = values.includes(previous) && previous !== "auto" ? previous : values[0];
                } catch (error) {
                    const values = previous && previous !== "auto" ? [previous, "auto"] : ["auto"];
                    setComboValues(modelWidget, values);
                    modelWidget.value = values[0];
                    console.error("Local LLM model refresh failed", error);
                }

                this.setDirtyCanvas(true, true);
            };

            const scheduleRefresh = () => {
                clearTimeout(timer);
                timer = setTimeout(refreshModels, 400);
            };

            for (const widget of [endpointWidget, apiKeyWidget, apiTypeWidget, timeoutWidget]) {
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

            scheduleRefresh();
            return result;
        };
    },
});
