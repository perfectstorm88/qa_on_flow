from flow.rule_expr import RuleExpr
from flow.flow_load import loadOneDir
import os
import sys
import json
import re
from pydash import py_
import ast
pythonPath = os.path.join(os.path.dirname(__file__), '..')
if pythonPath not in sys.path:
    sys.path.append(pythonPath)


class FlowMgr:
    def __init__(self, _dir):
        """需要加载流程图的目录
        """
        # 加载目录下的所有流程图
        flows, nodes, links = loadOneDir(_dir)
        # 为了加速，对链路中的表达式进行预编译
        pre_links = {}
        for k, _nodes in links.items():
            pre_links[k] = []
            for n_id, expr in _nodes:
                pre_links[k].append(
                    [n_id, ast.parse(expr) if len(expr) > 0 else None])

        self.flows = flows
        self.nodes = nodes
        self.links = links
        self.pre_links = pre_links
        self.func_map = {}

    def _next_question(self, question_seq, all_anwser):
        """获取下一个节点
        入参：
          question_seq 当前的问题编号
          all_anwser 累计的问题答案
        出参：
          next_id 下一个问题编号
          node_info 下一个问题节点的内容
        """
        _nodes = self.pre_links[question_seq]
        if len(_nodes) == 1:
            next_id = _nodes[0][0]
        else:
            # 先执行表达式
            default_node_id = None
            for n_id, expr_node in _nodes:
                if expr_node is None:
                    default_node_id = n_id
                result = RuleExpr(expr_node, all_anwser).exec()
                if result:
                    next_id = n_id
                    break
            # 采用默认节点
            if next_id is None:
                next_id = default_node_id
        return next_id, self.nodes[next_id]

    def registerFunc(self, _func_map):
        """注册处理函数,供外部进行注册
        """
        self.func_map.update(_func_map)

    def exec(self, question_seq, question_anwser, all_anwser, flow_name):
        """执行函数
        入参：
          question_seq 当前的问题编号，如果是第一个问题，为空
          question_anwser 当前问题的答案，为int或者string或者list或者对象
          all_anwser 累计的问题答案
          flow_name 流程名
          extend 扩展内容，例如token等,用于登录用户信息验证等
        出参:
          场景1、后端产生问题，返回问句，主要字段为：
            flag=contine
            question_seq: 问题编码
            question_type:问题类型：多选项、单选项、输入项、身高、体重、症状列表，发生频率、持续时间
            question_content: 问题内容
            question_option：数组，前端显示的候选项列表
            default_value: 默认值
          场景2、结束流程，结束问答，此时的主要字段为：
            flag=end
            flow_retsult_type:流程结果类型，例如"预问诊结果"、"导诊结果"、"体检结果"
            flow_result_detail:流程结果详细，当flag=end时，返回flow_retsult_type和flow_result_detail，前端根据type显示不同结果页面
        """

        ret = {}
        # 解析当前节点的答案
        if question_seq == '':
            question_seq = self.flows[flow_name]
        else:
            node_info = self.nodes[question_seq]
            all_anwser[node_info['主键']] = question_anwser
            if '后置处理' in node_info:
                func_map[node_info['后置处理']](all_anwser, question_anwser)

        next_id, node_info = self._next_question(question_seq, all_anwser)
        print('next_id', next_id, node_info)
        ret['flag'] = node_info['flag']
        # 判断下个节点的条件
        if node_info['flag'] == 'end':
            # 流程结果类型，例如"预问诊结果"、"导诊结果"、"体检结果"
            flow_retsult_type = node_info['question_content']
            ret['flow_retsult_type'] = flow_retsult_type
            # 流程结果详细，当flag=end时，返回flow_retsult_type和flow_result_detail，前端根据type显示不同结果页面
            ret['flow_result_detail'] = func_map[flow_retsult_type](all_anwser)
        else:
            ret['question_seq'] = next_id
            ret['question_content'] = node_info['question_content']
            ret['question_type'] = node_info['question_type']
            ret['question_option'] = node_info.get('question_option')
            ret['question_limit'] = node_info.get('question_limit')
            ret['default_value'] = node_info.get('default_value')
            ret['question_topic'] = node_info['主键']
            if '前置处理' in node_info:
                func_map[node_info['前置处理']](all_anwser, ret)
        return ret


if __name__ == '__main__':
    func_map = {
        "前置处理函数样例": lambda all_anwser, ret: print('这是一个前置处理函数样例()'),
        "后置处理函数样例": lambda all_anwser, question_anwser: print('这是一个前置处理函数样例'),
        "流程结果函数样例": lambda all_anwser: all_anwser,  # 返回流程结果,
        "个性主题推荐": lambda all_anwser: {'个性主题推荐', '这是流程结果函数样例'},  # 返回流程结果
        "体重估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:体重估算样例'),
        "身高估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:身高估算样例'),
        "体重估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:体重估算样例'),
    }
    flow_mgr = FlowMgr(os.path.join(os.path.dirname(__file__), '../flow_pos'))
    flow_mgr.registerFunc(func_map)
    print(flow_mgr.exec("", "", {}, '健康APP引导流程'))
    print(flow_mgr.exec("1750c3f1a1304e", "", {}, '健康APP引导流程'))
