# encoding: utf-8

from flow.flow_mgr import FlowMgr
from flask import jsonify
import json
from flask import Flask, request
import requests
import time
import re
import random
import hashlib
import datetime
import os
import sys

pythonPath = os.path.join(os.path.dirname(__file__), '.')
if pythonPath not in sys.path:
    sys.path.append(pythonPath)
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = "application/json;charset=utf-8"


# TODO flow进行解耦，把业务逻辑注册到flow_exec中
_func_map = {
    "前置处理函数样例": lambda all_anwser, ret: print('这是一个前置处理函数样例()'),
    "后置处理函数样例": lambda all_anwser, question_anwser: print('这是一个前置处理函数样例'),
    "流程结果函数样例": lambda all_anwser: all_anwser,  # 返回流程结果,
    "个性主题推荐": lambda all_anwser: {'个性主题推荐', '这是流程结果函数样例'},  # 返回流程结果
    "体重估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:体重估算样例'),
    "身高估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:身高估算样例'),
    "体重估算": lambda all_anwser, question_anwser: print('这是一个前置处理函数:体重估算样例'),
}
flow_mgr = FlowMgr(os.path.join(os.path.dirname(__file__), 'flow_pos'))
flow_mgr.registerFunc(_func_map)


@app.route('/api/p/qa', methods=['POST'])
def qa():
    """
    {"question_seq": "", "question_anwser": [],"all_anwser": {},"flow_name":"这是某某流程",'extend':{}}
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
    res = request.get_json()
    question_seq, question_anwser, all_anwser, flow_name, extend = res['question_seq'], res[
        'question_anwser'], res['all_anwser'], res['flow_name'], res.get('extend', {})
    all_anwser['extend'] = extend
    ret = flow_mgr.exec(question_seq, question_anwser, all_anwser, flow_name)
    return jsonify(ret)


if __name__ == '__main__':
    # from daozhen.inference import get_vord2vec_model
    # # get_vord2vec_model()
    app.run('0.0.0.0', port='6012')
