#      Copyright 2021. ThingsBoard
#  #
#      Licensed under the Apache License, Version 2.0 (the "License");
#      you may not use this file except in compliance with the License.
#      You may obtain a copy of the License at
#  #
#          http://www.apache.org/licenses/LICENSE-2.0
#  #
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.
from time import time
from typing import Union

from simplejson import dumps

from thingsboard_gateway.connectors.converter import Converter, log
from thingsboard_gateway.gateway.constant_enums import DownlinkMessageType
from thingsboard_gateway.gateway.proto.messages_pb2 import *


class GrpcDownlinkConverter(Converter):
    def __init__(self):
        self.__conversion_methods = {
            DownlinkMessageType.Response: self.__convert_response_msg,
            DownlinkMessageType.ConnectorConfigurationMsg: self.__convert_connector_configuration_msg,
            DownlinkMessageType.GatewayAttributeUpdateNotificationMsg: self.__convert_gateway_attribute_update_notification_msg,
            DownlinkMessageType.GatewayAttributeResponseMsg: self.__convert_gateway_attribute_response_msg,
            DownlinkMessageType.GatewayDeviceRpcRequestMsg: self.__convert_gateway_device_rpc_request_msg,
            DownlinkMessageType.UnregisterConnectorMsg: self.__convert_unregister_connector_msg
            }

    def convert(self, config, msg):
        try:
            basic_msg = FromServiceMessage()
            message_types = config.get("message_type")
            additional_message = config.get("additional_message")
            if not isinstance(message_types, list):
                message_types = [message_types]
            for message_type in message_types:
                self.__conversion_methods[message_type](basic_msg, msg, additional_message)
            return basic_msg
        except Exception as e:
            log.exception("[GRPC] ", e)
            return None

    @staticmethod
    def __convert_response_msg(basic_msg, msg, additional_message):
        if additional_message is not None:
            if additional_message.HasField('gatewayTelemetryMsg'):
                additional_message.gatewayTelemetryMsg.MergeFrom(GatewayTelemetryMsg())
            elif additional_message.HasField("gatewayAttributesMsg"):
                additional_message.gatewayTelemetryMsg.MergeFrom(GatewayTelemetryMsg())
            else:
                basic_msg.response.connectorMessage.MergeFrom(additional_message)
        basic_msg.response.status = ResponseStatus.Value(msg.name)

    @staticmethod
    def __convert_connector_configuration_msg(basic_msg, msg, additional_data=None):
        pass

    @staticmethod
    def __convert_gateway_attribute_update_notification_msg(basic_msg, msg, additional_data=None):
        ts = int(time()*1000)
        gw_attr_upd_notify_msg = GatewayAttributeUpdateNotificationMsg()
        gw_attr_upd_notify_msg.deviceName = msg['device']
        attr_notify_msg = AttributeUpdateNotificationMsg()
        for shared_attribute in msg['data']:
            ts_kv_proto = TsKvProto()
            ts_kv_proto.ts = ts
            kv = GrpcDownlinkConverter.__get_key_value_proto_value(shared_attribute, msg['data'][shared_attribute])
            ts_kv_proto.kv.MergeFrom(kv)
            attr_notify_msg.sharedUpdated.extend([ts_kv_proto])
        gw_attr_upd_notify_msg.notificationMsg.MergeFrom(attr_notify_msg)
        basic_msg.gatewayAttributeUpdateNotificationMsg.MergeFrom(gw_attr_upd_notify_msg)
        return basic_msg

    @staticmethod
    def __convert_gateway_attribute_response_msg(basic_msg, msg, additional_data=None):
        pass

    @staticmethod
    def __convert_gateway_device_rpc_request_msg(basic_msg, msg, additional_data=None):
        msg_data = msg['data']
        gw_to_device_rpc = GatewayDeviceRpcRequestMsg()
        gw_to_device_rpc.deviceName = msg['device']
        rpc_request_msg = ToDeviceRpcRequestMsg()
        rpc_request_msg.requestId = msg_data['id']
        rpc_request_msg.methodName = msg_data['method']
        if isinstance(msg_data['params'], dict):
            rpc_request_msg.params = dumps(msg_data['params'])
        else:
            rpc_request_msg.params = str(msg_data['params'])
        gw_to_device_rpc.rpcRequestMsg.MergeFrom(rpc_request_msg)
        basic_msg.gatewayDeviceRpcRequestMsg.MergeFrom(gw_to_device_rpc)
        return basic_msg

    @staticmethod
    def __convert_unregister_connector_msg(basic_msg, msg, additional_data=None):
        if msg is None:
            msg = b''
        unreg_msg = UnregisterConnectorMsg()
        unreg_msg.connectorKey = msg
        basic_msg.unregisterConnectorMsg.MergeFrom(unreg_msg)
        return basic_msg

    @staticmethod
    def __get_key_value_proto_value(key: str, value: Union[str, bool, int, float, dict]) -> KeyValueProto:
        key_value_proto = KeyValueProto()
        key_value_proto.key = key
        if isinstance(value, bool):
            key_value_proto.type = KeyValueType.BOOLEAN
            key_value_proto.bool_v = value
        elif isinstance(value, int):
            key_value_proto.type = KeyValueType.LONG_V
            key_value_proto.long_v = value
        elif isinstance(value, float):
            key_value_proto.type = KeyValueType.DOUBLE_V
            key_value_proto.double_v = value
        elif isinstance(value, str):
            key_value_proto.type = KeyValueType.STRING_V
            key_value_proto.string_v = value
        elif isinstance(value, dict):
            key_value_proto.type = KeyValueType.JSON_V
            key_value_proto.json_v = dumps(value)
        return key_value_proto
