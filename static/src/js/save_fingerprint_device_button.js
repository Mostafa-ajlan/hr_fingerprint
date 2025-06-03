/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, useState, onMounted } from "@odoo/owl";
// import { FormController } from "@web/views/form/form_controller";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { handleBiometricIoTConnectionFallbacks } from "./iot_implement_action";
import { IoTConnectionErrorDialog } from '@iot/iot_connection_error_dialog';



export class SaveFingerprintDeviceButton extends Component {
    static template = `hr_fingerprints.SaveFingerprintDeviceButton`;
    static props = {
        ...standardWidgetProps,
        action_type: { type: String }
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.http = useService('http');
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.iotBoxesBeforeConnection = [];
        this.action = ''
    }

    async saveFingerprintDeviceInfo() {
        this.action = 'save_fingerprint_device';
        const use_iot_box = this.props.record.data.use_iot_box;
        if (use_iot_box) {

            const args = [
                this.props.record.data.iot_device_id,
                this.action,
                this.props.record.data.name
            ];
            await handleBiometricIoTConnectionFallbacks(this.env, this.orm, args);
        } else {

        }
    }
    async iotSaveFingerprintDeviceInfo() { }

    async checkIotBoxConnection() {
        // await env.services.dialog.add(IoTConnectionErrorDialog, { iot_ip })

    }
    async derictSaveFingerprintDeviceInfo() { }

}

export const saveFingerprintDeviceButton = {
    component: SaveFingerprintDeviceButton,
    extractProps: ({ attrs }) => {
        const { action_type } = attrs;
        console.log('action_type', action_type);
        return {
            action_type
        };
    },
};
registry.category('view_widgets').add('save_fingerprint_device_info', saveFingerprintDeviceButton);
