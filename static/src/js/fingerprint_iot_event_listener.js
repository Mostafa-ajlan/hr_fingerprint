/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, onWillStart, useState } from "@odoo/owl";
import { useIotDevice } from '@iot/iot_device_hook';
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class FingerprintIoTEventListener extends Component {
    static template = `hr_fingerprints.FingerprintIoTEventListener`;
    static props = { ...standardWidgetProps };
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            value: '',
            iot_ip: null,
            identifier: null,
        });
        onWillStart(async () => {
            const deviceId = this.props.record.data.iot_device_id;
            const [device] = await this.orm.searchRead("iot.device", [['id', '=', deviceId[0]]], ['iot_ip', 'identifier'], { limit: 1 });
            if (device) {
                this.state.iot_ip = device.iot_ip;
                this.state.identifier = device.identifier;
            }
        });
        useIotDevice({
            getIotIp: () => this.state.iot_ip,
            getIdentifier: () => this.state.identifier,
            onValueChange: (data) => {
                this.state.value = data.value;
            },
        });
    }
}

export const fingerprintIoTEventListener = {
    component: FingerprintIoTEventListener,
};
registry.category('view_widgets').add('fingerprint_iot_event_listener', fingerprintIoTEventListener);