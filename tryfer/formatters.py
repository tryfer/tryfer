import json


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
