/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { handleDeviceNotConnected, buildParams } from "./iot_implement_action";

export class FingerprintIotWebsocket {
    jobs = {};
    notifyUser = true;

    constructor(bus_service, notification, orm) {
        this.notification = notification;
        this.bus_service = bus_service;
        this.orm = orm;
    }


    async addJob(args, notifyUser = false) {
        this.notifyUser = notifyUser;
        const { iotDeviceId, action, name, type, extraData } = args;
        let device;
        if (type === 'fp_device') {
            device = await orm.call("iot.device", "get_iot_box_data", [iotDeviceId, name])
        }
        else if (type === 'fp_user') {
            const res = await orm.searchRead("iot.device", [['id', '=', iotDeviceId]], ['iot_ip', 'identifier'], { limit: 1 });
            device = res && res[0];
        } else {
            throw new Error("Unsupported type: " + type);
        }
        if (!device) throw new Error("Failed to get iot info from iot devices");

        if ('connected' in device && !device.connected) {
            await handleDeviceNotConnected(env, device, action, name);
            return;
        }

        const uuid = extraData?.uuid;
        this.jobs[uuid] = device;

        if (this.notifyUser) {
            device._removeSendingNotification = this.notification.add(_t('Sending to biometric device %s...', device.name), {
                type: "info",
                sticky: true,
            });
        }

        // Timeout في حال لم يصل تأكيد
        const confirmationTimeout = setTimeout(() => {
            device._removeSendingNotification?.();
            this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), {
                title: (_t("Connection to biometric device failed ") + device.name),
                type: "danger",
            });
            delete this.jobs[uuid];
        }, 10000);

        try {
            await this.orm.call("iot.device", "biometric_action", [
                iotDeviceId,
                action,
                name,
                type,
                extraData,
                uuid,
            ]);
        } catch (e) {
            clearTimeout(confirmationTimeout);
            if (this.notifyUser) {
                this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), { type: "danger" });
            }
            throw e;
        }
    }

    onBiometricConfirmation(deviceId, uuid) {
        const device = this.jobs[uuid];
        device?._removeSendingNotification?.();
        this.notification.add(_t('Biometric operation completed on device %s', device?.name), {
            type: "success",
        });
        delete this.jobs[uuid];
    }
}

export const FingerprintIotWebsocketService = {
    dependencies: ["bus_service", "notification", "orm"],

    async start(env, { bus_service, notification, orm }) {
        let ws = new FingerprintIotWebsocket(bus_service, notification, orm);
        const iot_channel = await orm.call("iot.channel", "get_iot_channel", [0]);
        if (iot_channel) {
            bus_service.addChannel(iot_channel);
            bus_service.subscribe("biometric_confirmation", (payload) => {
                if (ws.jobs[payload["uuid"]]) {
                    ws.onBiometricConfirmation(payload["device_id"], payload["uuid"]);
                }
            });
        }
        return ws;
    },
};

registry.category("services").add("fingerprint_iot_websocket", FingerprintIotWebsocketService);