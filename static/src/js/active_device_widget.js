import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class ActiveDeviceWidget extends Component {
    static template = "hr_fingerprints.ActiveDeviceWidget";

    async ActiveDeviceWidgetClick() {
        this.props.record.data.active = !this.props.record.data.active;
    }

}

const activeDeviceWidget = {
    component: ActiveDeviceWidget,
};

registry.category("fields").add("active_device_widget", activeDeviceWidget);