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

/**
 * Get the devices from the ids stored in the localStorage
 * @param orm The ORM service
 * @param stored_content The list of devices in localStorage
 */
// async function getDevicesFromIds(orm, stored_content) {
//     return await orm.call("ir.actions.report", "get_devices_from_ids", [
//         0,
//         stored_content,
//     ]);
// }

/**
 * Send the report to the IoT device using longpolling
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices in localStorage to send the report to
 */
async function longpolling(env, orm, args) {
    const device = await orm.call("iot.device", "get_iot_box_data", [args[0], args[2]]).catch((error) => {
        throw error;
    });
    if (!device) {
        throw new Error("Failed to get iot info from iot devices");
    }

    if ('connected' in device && !device.connected) {
        if (args[1] == 'save_fingerprint_device_info') {

            if ('create' in device && !device.create) {
                env.services.notification.add(
                    _t("The device was not saved because it already existed.",
                        device.name), { type: "danger" });
            }
            else {
                env.services.notification.add(
                    _t("The device has been saved, but there is a problem connecting to the IoT device to retrieve all device data.",
                        device.iot_name), { type: "danger" });
            }
            await env.services.action.doAction({
                type: 'ir.actions.act_window_close'
            });
        } else {
            env.services.notification.add(
                _t("Device not connected. Check is connected correctly with IoT device .",
                    device.iot_name), { type: "danger" }
            );
        }
        return
    }

    const identifier = device.identifier;

    const longpollingHasFallback = true; // Prevent `IoTConnectionErrorDialog`
    await env.services.notification.add(_t("Sending to biometric %s...", device.name), { type: "info" });
    const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip: device.iot_ip, identifier });
    const params = {
        'iot_ip': device.iot_ip,
        'identifier': identifier,
        'name': device.name,
        'ip_address': device.ip_address,
        'port': device.port,
        'password': device.password,
        'protocol': device.protocol,
        'display_name': args[2], // Add the device display name to the iot object
    }
    const response = await iotDevice.action({ 'action': args[1], 'params': params }, longpollingHasFallback);
    console.log("response", response);
    await env.services.action.doAction({
        type: 'ir.actions.act_window_close'
    });
}

// async function showNotificationAndClose(env, message, type = "danger") {
//     await env.services.notification.add(_t(message), { type });
//     await env.services.action.doAction({ type: 'ir.actions.act_window_close' });
// }

// async function longpolling(env, orm, args) {
//     try {
//         const device = await orm.call("iot.device", "get_iot_box_data", [args[0], args[2]]);
//         if (!device) {
//             throw new Error("Failed to get IoT info from IoT devices");
//         }

//         const {
//             iot_ip,
//             iot_name,
//             name,
//             identifier,
//             ip_address,
//             port,
//             password,
//             protocol,
//             connected,
//             create
//         } = device;

//         if (!connected) {
//             const message = create
//                 ? _t("The device has been saved, but there is a problem connecting to the IoT device to retrieve all device data.", iot_name)
//                 : _t("The device was not saved because it already existed.", name);

//             await showNotificationAndClose(env, message);
//             return;
//         }

//         const params = [
//             iot_ip,
//             identifier,
//             name,
//             ip_address,
//             port,
//             password,
//             protocol,
//             args[2] // Add the device display name
//         ];

//         await env.services.notification.add(_t("Sending to biometric %s...", name), { type: "info" });

//         const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip, identifier });
//         const response = await iotDevice.action(
//             { action: args[1], params },
//             true // longpollingHasFallback
//         );

//         console.debug("IoT Device Response:", response);
//         await env.services.action.doAction({ type: 'ir.actions.act_window_close' });

//     } catch (error) {
//         await showNotificationAndClose(env, `An error occurred: ${error.message}`);
//     }
// }

/**
 * Try to send the report to the IoT device using longpolling, then fallback to the websocket
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices to send the report to
 */
export async function handleBiometricIoTConnectionFallbacks(env, orm, args) {
    args.push(uuid()); // Add a unique identifier to the args
    // Define the connection types in the order of executions to try
    const connectionTypes = [
        () => longpolling(env, orm, args),
        // () => env.services.fingerprint_iot_websocket.addBiomtrecJob(args, false),
    ];
    for (const connectionType of connectionTypes) {
        try {
            await connectionType();
            return;
        } catch {
            console.debug("Send action request failed, attempting another protocol.")
        }
    }

    // // Fail notification if all connections failed
    // env.services.notification.add(_t("Failed to send to printer."), { type: "danger" });
}




