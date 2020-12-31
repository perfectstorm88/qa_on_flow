import os
import json
import re
from pydash import py_


"""
keys_dict = [
  "输入方式",
  "默认值",
  "主键",
  "题目",
  "前置处理"
  "后置处理",
  "枚举值列表",
  "限制条件"
]
question_seq: 问题编码
question_type:问题类型：多选项、单选项、输入项、身高、体重、症状列表，发生频率、持续时间
question_content: 问题内容
question_option：数组，前端显示的候选项列表
default_value: 默认值
question_limit:输入限制
"""


def parseNodeText(t):
    ret = {'flag': 'continue'}  # start、end、continue、子流程
    t = t.replace('：', ':').replace(' ', '').replace(
        '<div>', ' ').replace('</div>', ' ').replace('<br>', ' ').strip()
    lines = list(filter(lambda x: len(x) > 0, t.split(' ')))
    key = None
    title = lines[0]
    keys = re.findall(r'(?<=\$).+?(?=\$)', title)
    if len(keys) > 0:
        key = keys[0]
        title = title.replace('$', '')
    if '开始:' in title:
        ret['flag'] = 'start'
        ret['question_content'] = title.replace('开始:', '')
    elif '结束:' in title:
        ret['flag'] = 'end'
        ret['question_content'] = title.replace('结束:', '')
    elif '子流程：' in title:
        # 加载子流程,并进行合并
        pass
    else:
        ret['question_content'] = title
        ret['主键'] = key

    for line in lines[1:]:
        str_list = line.split(':')
        prefix = str_list[0]
        if prefix == '输入方式':
            ret['question_type'] = str_list[1]
            if ret['question_type'] in ['单选项', '多选项']:
                ret['question_option'] = str_list[2].split('、')
            if ret['question_type'] in ['数值输入框']:
                ret['question_limit'] = str_list[2]
        elif prefix == '默认值':
            ret['default_value'] = str_list[1]
        else:
            ret[prefix] = str_list[1]
    return ret


def load_one_flow(f):
    with open(f, 'rt', encoding='utf-8') as f:
        flow = json.load(f)
    # step1 找到流程开始节点
    start_terminators = []
    for k, e in flow['diagram']['elements']['elements'].items():
        if e['name'] == "terminator":
            if e['textBlock'][0]['text'].startswith('开始'):
                start_terminators.append(e)
    if len(start_terminators) == 0:
        raise Exception('没有发现 开始流程')

    # step2 找到所有的连线，构建from -》to 的map
    start_node = start_terminators[0]
    all_links = {}  # from =>(id,text)
    for k, e in flow['diagram']['elements']['elements'].items():
        if e['name'] != 'linker':
            continue
        _from, _to = py_.get(e, 'from.id'), py_.get(e, 'to.id')
        if _from is None or _to is None:
            print('发现没有from 和to 的linker')
            continue
        if _from not in all_links:
            all_links[_from] = []
        all_links[_from].append(
            [py_.get(e, 'to.id'), e['text'].replace('\n', ' ').strip()])
    print(json.dumps(start_terminators, indent=2, ensure_ascii=False))

    visited = {}  # id ->node_info
    links = {}  # 有效的link

    def visit_node(e):
        """递归遍历
        """
        if e['id'] in visited:
            return
        text = e['textBlock'][0]['text']
        visited[e['id']] = parseNodeText(text)
        print(e['id'], visited[e['id']])
        if e['id'] not in all_links:  # 是终点
            return
        links[e['id']] = all_links[e['id']]
        for (e_id, condition) in all_links[e['id']]:
            print(e['id'], "==>", e_id, ":", condition)
            visit_node(flow['diagram']['elements']['elements'][e_id])

    # 构建流程图
    flows = {}  # flowname -> start_node
    for start_node in start_terminators:
        text = start_node['textBlock'][0]['text']
        flow_name = text.replace('开始：', '').replace('开始:', '').strip()
        print('开始构建flow:', flow_name)
        flows[flow_name] = start_node['id']
        visit_node(start_node)

    return flows, visited, links


def loadOneDir(_dir=os.path.join(os.path.dirname(__file__), '../flow_pos')):
    flows, visited, links = {}, {}, {}
    onlyfiles = [f for f in os.listdir(_dir) if f.endswith('.pos')]
    for f in onlyfiles:
        _flows, _visited, _links = load_one_flow(os.path.join(_dir, f))
        flows.update(_flows)
        visited.update(_visited)
        links.update(_links)
    return flows, visited, links


if __name__ == '__main__':
    loadOneDir()
