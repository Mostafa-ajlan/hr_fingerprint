/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";


export class ConnectionStatusField extends Component {
    static template = "hr_fingerprints.ConnectionStatus";
    static props = {
        ...standardWidgetProps,
        *optionalProps() {
            yield "record";
            yield "name";
        }
    };

    get statusInfo() {
        const status = this.props.record.data[this.props.name] || "unknown";
        const statusMap = {
            connected: {
                text: this.env._t("Connected"),
                icon: "fa-check-circle",
                class: "text-success",
                bgClass: "bg-success-light"
            },
            disconnected: {
                text: this.env._t("Disconnected"),
                icon: "fa-times-circle",
                class: "text-danger",
                bgClass: "bg-danger-light"
            },
            unknown: {
                text: this.env._t("Unknown"),
                icon: "fa-question-circle",
                class: "text-warning",
                bgClass: "bg-warning-light"
            }
        };
        return statusMap[status];
    }
}

registry.category("fields").add("connection_status_header", ConnectionStatusField);