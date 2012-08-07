import json
import struct
import socket

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport

from tryfer._thrift.zipkinCore import ttypes


def hex_str(n):
    return '%0.16x' % (n,)


def json_formatter(trace, annotations):
    json_trace = {
        'trace_id': hex_str(trace.trace_id),
        'span_id': hex_str(trace.span_id),
        'name': trace.name,
        'annotations': []
    }

    if trace.parent_span_id:
        json_trace['parent_span_id'] = hex_str(trace.parent_span_id)

    for annotation in annotations:
        json_annotation = {
            'key': annotation.name,
            'value': annotation.value,
            'type': annotation.annotation_type
        }

        if annotation.endpoint:
            json_annotation['host'] = {
                'ipv4': annotation.endpoint.ipv4,
                'port': annotation.endpoint.port,
                'service_name': annotation.endpoint.service_name
            }

        json_trace['annotations'].append(json_annotation)

    return json.dumps([json_trace])


def ipv4_to_long(ipv4):
    return struct.unpack('!L', socket.inet_aton(ipv4))[0]


def base64_thrift(thrift_obj):
    trans = TTransport.TMemoryBuffer()
    tbp = TBinaryProtocol.TBinaryProtocolAccelerated(trans)

    thrift_obj.write(tbp)

    return trans.getvalue().encode('base64').strip()


def base64_thrift_formatter(trace, annotations):
    thrift_annotations = []

    for annotation in annotations:
        host = None
        if annotation.endpoint:
            host = ttypes.Endpoint(
                ipv4=ipv4_to_long(annotation.endpoint.ipv4),
                port=annotation.endpoint.port,
                service_name=annotation.endpoint.service_name)

        thrift_annotations.append(ttypes.Annotation(
            timestamp=annotation.value,
            value=annotation.name,
            host=host))

    thrift_trace = ttypes.Span(
        trace_id=trace.trace_id,
        name=trace.name,
        id=trace.span_id,
        parent_id=trace.parent_span_id,
        annotations=thrift_annotations
    )

    return base64_thrift(thrift_trace)
