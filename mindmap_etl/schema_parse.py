# coding: utf-8

from encoder import XML2Dict
import dpath.util as dp
import re
from lxml import etree

def read(p):
    xml = XML2Dict()
    with open(p, 'r', encoding='utf-8') as f:
        s = f.read()
        root = etree.fromstring(s.encode())
        
        # Remove namespace prefixes
        for elem in root.getiterator():
            elem.tag = etree.QName(elem).localname
        # Remove unused namespace declarations
        etree.cleanup_namespaces(root)

        s = etree.tostring(root).decode()
        the_dict = xml.parse(s)
        return the_dict

class AttrDict(dict):
    '一个可以用“.key”代替“["key"]”获取属性的字典。用法与字典相同，只是多出了通过.获取属性。'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

def debug(*x,**y):
    print(*x,**y)

def to_attr_dict(d):
    if isinstance(d, dict):
        for i in d:
            d[i] = to_attr_dict(d[i])
        return AttrDict(d)
    elif isinstance(d, list):
        for i in range(len(d)):
            d[i] = to_attr_dict(d[i])
        return d
    else:
        return d

def dict2list(d):
    if isinstance(d, dict):
        return [d]
    elif isinstance(d, list):
        return d
    else:
        return d

def extract_shape_rels(path):
    d = to_attr_dict(read(path))
    all_shapes = {}
    origin = {} # Circle, ID:'', fields:[], 
    node_schemas = {} # Rectangle
    edge_schemas = {} # Diamond
    node_extractors = {} # default
    edge_extractors = {} # default
    default_dtype = 'TEXT'

    
    rels = []

    for rel in d.Map.Relationships.Relationship:
        s, t = rel.ConnectionGroup
        sid = s.Connection['@ObjectReference'].OIdRef
        tid = t.Connection['@ObjectReference'].OIdRef
        rels.append([sid, tid])
        if 'FloatingTopics' in rel:

            m =  dp.values(rel.FloatingTopics, '**/VerticalCalloutFloatingTopicShape')
            name = rel.FloatingTopics.Topic['@Text'].PlainText
            oid = rel.FloatingTopics['@Topic'].OId

            if m == ['urn:mindjet:RectangleBalloon']:
                # 解析边的schema，类型为正方形
                edge_schemas[name] = dict(
                    # TODO: edge fields
                    # fields = {i['@Text'].PlainText:{
                    #     'dtype':default_dtype,
                    #     'type': 'field',
                    #     'name': i['@Text'].PlainText,
                    #     'id': i['#Topic'].OId,
                    #     } for i in dict2list(t.SubTopics.Topic)},
                    type='edge_schema',
                    name=name,
                    id=oid,
                    from_id=sid,
                    to_id=tid,
                )


                all_shapes[oid] = edge_schemas[name]
                # TODO: all_shapes.update({v['id']:v for v in edge_schemas[name]['fields'].values()})
            
            elif m == [] or m == ['urn:mindjet:Capsule']:
                # 解析边的extractor，类型为马蹄形

                edge_extractors[name] = dict(
                    # TODO： edge fields
                    # fields = {
                    #     i['@Text'].PlainText:{
                    #         'dtype':default_dtype,
                    #         'type': 'field',
                    #         'name': i['@Text'].PlainText,
                    #         'id': i['#Topic'].OId,
                    #     } for i in dict2list(t.SubTopics.Topic)},
                    type='edge_extractor',
                    name=name,
                    id=oid,
                    schema=None,
                    from_id=sid,
                    to_id=tid,
                    condition=None
                )
                
                # 收集条件判断语句
                if 'SubTopics' in rel.FloatingTopics.Topic:
                    for i in dict2list(rel.FloatingTopics.Topic.SubTopics.Topic):
                        if dp.values(i, '**/IconType') == ['urn:mindjet:QuestionMark']:
                            print('debug: condition:', i['@Text'].PlainText, name)
                            edge_extractors[name]['condition'] = eval(i['@Text'].PlainText)
                    
                    
                # 提取超链接形式标识的edge schema：
                url =  dp.values(rel.FloatingTopics.Topic, "@Hyperlink/Url")
                if url:
                    debug(name ,url)
                    m = re.search("\[@OId='([^']+)'\]", url[0])
                    if m:
                        rels.append([oid, m.group(1)])

                all_shapes[oid] = edge_extractors[name]
                # TODO: all_shapes.update({v['id']:v for i,v in edge_extractors[name]['fields'].values()})
            else:
                print('unkown edge:', m)

    def get_subtopics_list(subtopics):
        if '@Topic' in subtopics:
            subtopics.Topic['#Topic'] = subtopics['@Topic']
        return dict2list(subtopics.Topic)


    for t in dict2list(d.Map.OneTopic.Topic.FloatingTopics.Topic):
        m =  dp.values(t, '**/VerticalLabelFloatingTopicShape')
        
        if not '@Text' in t: # 跳过空白的浮动主题
            continue

        name = t['@Text'].PlainText
        oid = t['#Topic'].OId
        if '@Topic' in t.SubTopics:
            t.SubTopics.Topic['#Topic'] = t.SubTopics['@Topic']

        # 解析节点schema，类型为长方形节点
        if m == ['urn:mindjet:Rectangle']:
            node_schemas[name] = dict(
                fields={i['@Text'].PlainText:{
                        'dtype':i.SubTopics.Topic['@Text'].PlainText if 'SubTopics' in i else default_dtype,
                        'type': 'field',
                        'name': i['@Text'].PlainText,
                        'id': i['#Topic'].OId,
                        'nullable': (dp.values(i, '**/IconType') == ["urn:mindjet:PadlockUnlocked"])
                    } for i in dict2list(t.SubTopics.Topic)},
                pk='',
                type='node_schema',
                name=name,
                id=oid,
            )

            pks = [i['@Text'].PlainText for i in dict2list(t.SubTopics.Topic) if dp.values(i, '**/IconType') == ["urn:mindjet:Key"]]
            if len(pks) != 1:
                raise ValueError("Only one PK must be given.")
            node_schemas[name]['pk'] = pks[0]

            all_shapes[oid] = node_schemas[name]
            all_shapes.update({v['id']:v for v in node_schemas[name]['fields'].values()})

        # 解析原始输入schema，类型为圆形节点
        elif m == ['urn:mindjet:Circle']:

            origin[name] = dict(
                fields = {i['@Text'].PlainText:{
                    'type': 'field',
                    'name': i['@Text'].PlainText,
                    'id': i['#Topic'].OId,
                    } for i in dict2list(t.SubTopics.Topic)},
                type='origin',
                name=name,
                id=oid,
            )

            all_shapes[oid] = origin[name]
            all_shapes.update({v['id']:v for v in origin[name]['fields'].values()})

        # 解析节点提取器，类型为马蹄形
        elif m == [] or m == ['urn:mindjet:Capsule']:
            
            node_extractors[name] = dict(
                fields = {i['@Text'].PlainText:{
                    'type': 'field',
                    'name': i['@Text'].PlainText,
                    'id': i['#Topic'].OId,
                    'from': None
                    } for i in get_subtopics_list(t.SubTopics) if dp.values(i, '**/IconType') != ['urn:mindjet:QuestionMark']},
                type='node_extractor',
                name=name,
                id=oid,
                schema=None,
                condition=None
            )

            # 收集条件判断语句
            for i in dict2list(t.SubTopics.Topic):
                if dp.values(i, '**/IconType') == ['urn:mindjet:QuestionMark']:
                    print('debug: condition:', i['@Text'].PlainText, name)
                    node_extractors[name]['condition'] = eval(i['@Text'].PlainText)
            
            # 提取超链接形式标识的node schema：
            url =  dp.values(t, "@Hyperlink/Url")
            if url:
                debug(name, url)
                m = re.search("\[@OId='([^']+)'\]", url[0])
                if m:
                    rels.append([oid, m.group(1)])

            all_shapes[oid] = node_extractors[name]
            all_shapes.update({v['id']:v for v in node_extractors[name]['fields'].values()})
        else:
            debug('unknown:', m)
    
    # 构建链接

    for s,t in rels:
        type_ = (all_shapes[s]['type'], all_shapes[t]['type'])
        if type_ == ('field', 'field'):
            # 字段对应关系
            all_shapes[t]['from'] = all_shapes[s]

        elif type_ == ('edge_extractor', 'edge_schema'):
            # 边提取器到边schema对应关系
            all_shapes[s]['schema'] = all_shapes[t]

        elif type_ == ('node_extractor', 'node_schema'):
            # 节点提取器到节点schema对应关系
            all_shapes[s]['schema'] = all_shapes[t]

        elif type_ == ('node_schema', 'node_schema'):
            # 边schema对应关系
            for i in edge_schemas:
                if (edge_schemas[i]['from_id'], edge_schemas[i]['to_id']) == (s, t):
                    edge_schemas[i]['from'] = all_shapes[s]
                    edge_schemas[i]['to'] = all_shapes[t]

        elif type_ == ('node_extractor', 'node_extractor'):
            # 边提取器的关系
            for i in edge_extractors:
                if (edge_extractors[i]['from_id'], edge_extractors[i]['to_id']) == (s, t):
                    edge_extractors[i]['from'] = all_shapes[s]
                    edge_extractors[i]['to'] = all_shapes[t]
        
    oname = list(origin.keys())[0]
    for n, v in node_extractors.items():
        # 处理节点提取器的默认字段，默认从origin获取同名的
        for f in v['fields']:
            if v['fields'][f]['from'] is None:
                if (f in origin[oname]['fields']):
                    v['fields'][f]['from'] = origin[oname]['fields'][f]
                else:
                    debug('Field %s of %s has no input field.'%(f, n))

        # 处理节点提取器的默认schema，默认从node_schemas获取同名的
        if v['schema'] is None:
            if n in node_schemas:
                v['schema'] = node_schemas[n]
            else:
                debug('Node extractor %s has no schema.'%(n))
    
    for e, v in edge_extractors.items():
        # 处理边提取器的默认schema，默认从edge_schemas获取同名的
        if v['schema'] is None:
            if e in edge_schemas:
                v['schema'] = edge_schemas[e]
            else:
                debug('Edge extractor %s has no schema.'%(e))

    return (
        to_attr_dict(origin),
        to_attr_dict(node_schemas),
        to_attr_dict(edge_schemas),
        to_attr_dict(node_extractors),
        to_attr_dict(edge_extractors),
    )
