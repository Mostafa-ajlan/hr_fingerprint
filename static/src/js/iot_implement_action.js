/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser"
import { DeviceController } from "@iot/device_controller";



/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 * Copied beacause if imported from web import too many other modules
 * 
 * @returns {string}
 */
function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function buildParams(device, args, extraData) {
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

    // استخدام الإجراء المحدد أو الافتراضي إذا لم يكن موجوداً
    const builder = actionBuilders[action] || actionBuilders.default;
    return builder();
}

// async function handleDeviceNotConnected(env, device, action, name) {
//     if (action === 'save_fingerprint_device_info') {
//         if ('create' in device && !device.create) {
//             env.services.notification.add(
//                 _t("The device was not saved because it already existed.", name), { type: "danger" });
//         } else {
//             env.services.notification.add(
//                 _t("The device has been saved, but there is a problem connecting to the IoT device to retrieve all device data.", device.iot_name), { type: "danger" });
//         }
//         await env.services.action.doAction({ type: 'ir.actions.act_window_close' });
//     } else {
//         env.services.notification.add(
//             _t("Device not connected. Check is connected correctly with IoT device.", device.iot_name), { type: "danger" }
//         );
//     }
// }
/**
 * General function to send action to IoT device and handle notifications.
 */
async function sendIoTAction(env, device, action, params) {
    const identifier = device.identifier;

    const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip: device.iot_ip, identifier });
    await env.services.notification.add(_t("Sending to %s biometric Device...", device.name), { type: "info" });
    try {
        const response = await iotDevice.action({ action, params }, true);
        await env.services.action.doAction({ type: 'ir.actions.act_window_close' });
    } catch (error) {
        env.services.notification.add(_t("IoT action failed: %s", error.message), { type: "danger" });
        throw error;
    }
}

// async function saveFingerprintDeviceInfo(env, orm, args) {
//     // const iotIsConnect = await env.services.iot_longpolling.checkConnection(device.iot_ip);

//     const { iot_device, action, name, extraData } = args;
//     const device = await orm.call("iot.device", "get_iot_box_data", [iot_device, name]);
//     if (!device) throw new Error("Failed to get iot info from iot devices");
//     if ('connected' in device && !device.connected) {
//         await handleDeviceNotConnected(env, device, action, name);
//         return;
//     }
//     const params = buildParams(device, args, extraData);
//     await sendIoTAction(env, device, action, params);

// }

async function longpolling(env, orm, args) {

    try {
        const res = await orm.searchRead("iot.device", [['id', '=', args.iot_device[0]]], ['iot_ip', 'identifier', 'name', 'connected'], { limit: 1 });
        const device = res && res[0];

        if (!device) throw new Error("Failed to get iot info from iot devices");
        const isConnected = await env.services.iot_longpolling.checkConnection(device.iot_ip, device.identifier);
        if (!isConnected.result) {
            env.services.notification.add(
                _t("Please make sure that the %s device is connected to the iot device.", device.name),
                { type: "danger" }
            );
            throw new Error("Device is not connected");
            // return;
        }

        const params = buildParams(device, args, args.extraData);
        await sendIoTAction(env, device, args.action, params);

    } catch (error) {
        env.services.notification.add(_t("Check Connecting IoT Device : %s", error.message), { type: "danger" });
        throw error;
    }

}

export async function handleBiometricIoTConnectionFallbacks(env, orm, args) {
    args.extraData = args.extraData || {};
    args.extraData.uuid = uuid(); // Add a unique identifier to the params
    const connectionTypes = [
        () => longpolling(env, orm, args),
    ];
    for (const connectionType of connectionTypes) {
        try {
            await connectionType();
            return;
        } catch {
            console.log("iiiiiiiiiiiiiiiiiiiiiiii")
            console.debug("Send action request failed, attempting another protocol.")
        }
    }

}
export async function handleBiometricIoTConnectionFallbacks2(env, orm, args) {
    args.extraData = args.extraData || {};
    args.extraData.uuid = uuid(); // Add a unique identifier to the params
    try {
        await longpolling(env, orm, args);
    } catch (error) {
        console.log("iiiiiiiiiiiiiiiiiiiiiii")
        // إذا فشل الاتصال، نرمي الاستثناء مباشرة ليتم منعه في الواجهة الأمامية
        throw error;
    }
}





