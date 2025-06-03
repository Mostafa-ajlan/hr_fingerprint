import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class FingerprintIotWebsocket {
    jobs = {};
    notifyUser = true;

    constructor(bus_service, notification, orm) {
        this.notification = notification;
        this.bus_service = bus_service;
        this.orm = orm;
    }

    async addBiomtrecJob(args, notifyUser = true) {
        console.log(args, "argsargsargsargsargsargs");
        this.notifyUser = notifyUser;
        const [iot_device_id, payload, uuid] = args;
        console.log("addBiomtrecJob", iot_device_id, payload, uuid);

        const iot = await this.orm.call("iot.device", "get_iot_box_data", [iot_device_id]).catch((error) => {
            console.error("Failed to get IoT info", error);
            throw error;
        });
        console.log("iot", iot);

        const [ip, identifier, name] = iot;

        this.jobs[uuid] = {
            ip,
            identifier,
            display_name: name,
        };

        const iotPayload = {
            type: "scan_fingerprint",
            uuid: uuid,
            payload: payload || {},
        };

        this.bus_service.sendNotification({
            channel: `iot_jsonrpc:${ip}`,
            payload: {
                jsonrpc: "2.0",
                method: "call",
                params: {
                    device_identifier: identifier,
                    message: iotPayload,
                },
            },
        });

        if (this.notifyUser) {
            this.jobs[uuid]._removeWaitingNotification = this.notification.add(_t("Waiting for fingerprint..."), {
                type: "info",
                sticky: true,
            });
        }

        setTimeout(() => {
            if (this.jobs[uuid]) {
                this.jobs[uuid]._removeWaitingNotification?.();
                this.notification.add(_t("No fingerprint response received. Check IoT connection."), {
                    type: "danger",
                });
                delete this.jobs[uuid];
            }
        }, 15000);
    }

    onFingerprintConfirmation(deviceId, jobId) {
        const job = this.jobs[jobId];
        if (!job) return;

        job._removeWaitingNotification?.();
        this.notification.add(_t("Fingerprint scan completed on device %s", job.display_name), {
            type: "success",
        });

        delete this.jobs[jobId];
    }
}

export const FingerprintIotWebsocketService = {
    dependencies: ["bus_service", "notification", "orm"],

    async start(env, { bus_service, notification, orm }) {
        let ws = new FingerprintIotWebsocket(bus_service, notification, orm);
        console.log("FingerprintIotWebsocketService started", ws);
        const iot_channel = await orm.call("iot.channel", "get_iot_channel", [0]);

        if (iot_channel) {
            bus_service.addChannel(iot_channel);
            bus_service.subscribe("fingerprint_confirmation", (payload) => {
                const jobId = payload["uuid"];
                if (ws.jobs[jobId]) {
                    ws.onFingerprintConfirmation(payload["device_identifier"], jobId);
                }
            });
        }

        return ws;
    },
};

registry.category("services").add("fingerprint_iot_websocket", FingerprintIotWebsocketService);
