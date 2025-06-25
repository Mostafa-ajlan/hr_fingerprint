/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class BiometricIotWebsocket {
    jobs = {};
    notifyUser = true;

    constructor(bus_service, notification, orm) {
        this.notification = notification;
        this.bus_service = bus_service;
        this.orm = orm;
    }


    async buildParams(device, args, extraData) {
        const { action } = args;
        const actionBuilders = {
            // حفظ معلومات جهاز البصمة
            save_fingerprint_device_info: () => ({
                iot_ip: device.iot_ip,
                identifier: device.identifier,
                // display_name: args.name,
                ...extraData,
            }),
            // الإجراء الافتراضي
            default: () => ({
                iot_ip: device.iot_ip,
                identifier: device.identifier,
                ...extraData,
            }),
        };

        const builder = actionBuilders[action] || actionBuilders.default;
        return builder();
    }

    async addJob(args, notifyUser = false) {
        this.notifyUser = notifyUser;
        const uuid = args.extraData.uuid;
        const res = await this.orm.searchRead("iot.device", [['id', '=', args.iot_device[0]]], ['iot_id', 'iot_ip', 'identifier', 'name', 'connected'], { limit: 1 });
        const device = res && res[0];
        if (!device) throw new Error("Failed to get iot info from iot devices");
        const params = await this.buildParams(device, args, args.extraData);
        this.jobs[uuid] = [device];

        if (this.notifyUser) {
            device._removeSendingNotification = this.notification.add(_t('Sending to device %s...', device["name"]), {
                type: "info",
                sticky: true,
            });
        }
        // const confirmationTimeout = setTimeout(() => {
        //     device._removeSendingNotification?.();
        //     this.notification.add(_t("Connection to device failed %s", device["name"]), { type: "danger" });
        //     delete this.jobs[uuid];
        // }, 10000);

        try {
            await this.orm.call("hr.fingerprint.device", "render_and_send", [device, args.action, params]);
        } catch (e) {
            // clearTimeout(confirmationTimeout);
            // if (this.notifyUser) {
            //     this.notification.add(_t("Check IoT Box connection. Try restarting if needed."), { type: "danger" });
            // }
            throw e;
        }
    }

    // onActionConfirmation(deviceId, uuid) {
    //     if (!this.jobs[uuid]) return;
    //     const jobIndex = this.jobs[uuid].findIndex((element) => element && element["identifier"] === deviceId);
    //     const device = this.jobs[uuid][jobIndex];

    //     device._removeSendingNotification?.();
    //     this.notification.add(_t('Operation completed on device %s', device["name"]), {
    //         type: "success",
    //     });
    //     delete this.jobs[uuid][jobIndex];
    // }
}

export const BiometricIotWebsocketService = {
    dependencies: ["bus_service", "notification", "orm", "multi_tab"],

    async start(env, { bus_service, notification, orm, multi_tab }) {
        let ws = new BiometricIotWebsocket(bus_service, notification, orm);

        const notifySuccess = async (message, content) => {
            if ('operation' in message && message.action_type == 'save_fingerprint_device_info') {
                notification.add(_t(content, message.device_identifier, message.operation || ''), {
                    type: 'success',
                });
                // await action.doAction({ type: 'ir.actions.act_window_close' });
                await action.doAction({
                    type: 'ir.actions.client',
                    tag: 'reload',
                    params: {
                        model: 'hr.fingerprint.device',
                        view_type: 'list',
                    },
                });

            }
            else if (message.action_type === 'live_capture') {
                notification.add(_t(content, message.device_identifier, message.fingerprint_type, message.punch_type), {
                    type: 'success',
                });
            }
            else {
                notification.add(_t(content, message.device_identifier), {
                    type: 'success',
                });
            }
        };

        const handleNotification = (message) => {
            console.log("BiometricIotWebsocketService")
            if (!multi_tab.isOnMainTab()) return;

            const actionMessages = {
                save_fingerprint_device_info: 'A %s device has been saved successfully %s.',
                fetch_user: 'Fetched users data successfully from %s device.',
                download_attendance: 'Downloaded attendance data successfully from %s device.',
                download_template: 'Downloaded template data successfully from %s device.',
                // clear_data: 'Cleared all data successfully from %s device.',
                shutdown_device: 'The device %s has been successfully turned off.',
                reboot_device: 'The device %s has been successfully reboot.',
                sync_time: 'The device %s has been successfully sync time.',
                create_or_update_user: 'User/Users created or updated successfully to %s device.',
                create_or_update_users: 'User/Users created or updated successfully to %s device.',
                delete_user: 'User/Users deleted successfully from %s device.',
                live_capture: 'Fingerprint registered from %s device. [Type: %s, Punch: %s]',
            };

            const logPrefix = 'Fingerprint Notification:';
            console.log(`${logPrefix} ${message.action_type}`, message);

            if (actionMessages[message.action_type]) {
                notifySuccess(message, actionMessages[message.action_type]);
            }
        };

        const iotChannel = await orm.call("iot.fingerprint.channel", "get_iot_channel", [0]);


        if (iotChannel) {
            bus_service.addChannel(iotChannel);
            bus_service.subscribe("fingerprint_iot_devices", handleNotification);
            // bus_service.subscribe("fingerprint_iot_devices", (payload) => {
            //     if (payload.uuid && ws.jobs[payload.uuid]) {
            //         ws.onActionConfirmation(payload.device_identifier, payload.uuid);
            //     }
            // });
        }
        return ws;
    },
};

registry.category("services").add("biometric_iot_websocket", BiometricIotWebsocketService);