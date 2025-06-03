/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, useState } from "@odoo/owl";
// import { FormController } from "@web/views/form/form_controller";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { handleBiometricIoTConnectionFallbacks } from "./iot_implement_action";


export class FetchHrFingerprintDeviceInfo extends Component {
    static template = `hr_fingerprints.FetchHrAttDeviceInfo`;
    static props = { ...standardWidgetProps };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.http = useService('http');
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.action = ''
    }
    get use_iot_box() {
        return this.props.record.data.use_iot_box;
    }

    async fetchDeviceInfo() {
        this.action = 'get_device_info';
        const use_iot_box = this.props.record.data.use_iot_box;
        if (use_iot_box) {
            const args = [
                this.props.record.data.iot_device_id[0],
                this.action
            ];
            await handleBiometricIoTConnectionFallbacks(this.env, this.orm, args);
        } else {

        }

    }

}

export const fetchHrFingerprintDeviceInfo = {
    component: FetchHrFingerprintDeviceInfo,
};
registry.category('view_widgets').add('fingerprint_device_info', fetchHrFingerprintDeviceInfo);
