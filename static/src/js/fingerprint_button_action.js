// File: hr_fingerprint/static/src/js/fingerprint_button_action.js

/** OWL Component Example using Odoo 18 style **/
import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart, useState, onMounted } from '@odoo/owl';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { handleBiometricIoTConnectionFallbacks } from "./iot_implement_action";

export class FingerprintButtonAction extends Component {
    static template = 'hr_fingerprints.FingerprintButtonAction';
    static props = {
        // ...standardFieldProps,
        ...standardWidgetProps,
        action: { type: String, optional: true },
        icon: { type: String, optional: true },
        text: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.http = useService('http');
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.iotBoxesBeforeConnection = [];
        this.action = useService("action");
    }
    get connection_mode() {
        return this.props.record.data.connection_mode;
    }

    async onClickFingerprintButton() {
        if (this.connection_mode == 'iot') {
            await this.handleIoTMode();
        }
        else if (this.connection_mode == 'push') {
            await this.handlePushMode();
        }
        else {
            await this.handleDirectMode();
        }
    }

    async handleIoTMode() {
        const args = [
            this.props.record.data.iot_device_id,
            this.props.action,
            this.props.record.data.name
        ];
        await handleBiometricIoTConnectionFallbacks(this.env, this.orm, args);
    }

    async handlePushMode() {
        if (this.props.action === 'save_fingerprint_device_info') {
            const serialNumber = this.props.record.data.serial_number;
            const deviceName = this.props.record.data.name || _t('Untitled Device');
            const connectionMode = this.props.record.data.connection_mode;

            if (!serialNumber) {
                this.notification.add(_t("Please set the serial number for the device."), {
                    type: "warning",
                });
                return;
            }

            try {
                const [deviceId] = await this.orm.create("hr.fingerprint.device", [{
                    serial_number: serialNumber,
                    name: deviceName,
                    connection_mode: connectionMode,
                    // active: false,
                }]);
                console.log("Created Device ID:", deviceId);

                if (!deviceId) {
                    this.notification.add(_t("Error when creating the device record."), {
                        type: "danger",
                    });
                    return;
                }

                this.notification.add(_t("Device created successfully."), {
                    type: "success",
                });

                await this.action.doAction({ type: 'ir.actions.act_window_close' });
                // await this.action.doAction({ type: 'ir.actions.client', tag: 'reload' });
            } catch (error) {
                console.error("Error creating device:", error);
                this.notification.add(_t("An unexpected error occurred."), {
                    type: "danger",
                });
            }
        }
    }

    async handleDirectMode() { }

}
export const fingerprintButtonAction = {
    component: FingerprintButtonAction,
    extractProps: ({ attrs }) => {
        const { action, icon, text } = attrs;
        console.log("My Options: ", action);
        return {
            action,
            icon: icon || '',
            text,
        };
    },
};

registry.category('view_widgets').add('fingerprint_button_action', fingerprintButtonAction);
