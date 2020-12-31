import os
import sys

pythonPath = os.path.join(os.path.dirname(__file__), '..')
if pythonPath not in sys.path:
    sys.path.append(pythonPath)
import requests
import unittest

from flow.flow_load import  parseNodeText


class TestAPI(unittest.TestCase):
    def setUp(self):
        print("测试开始")

    #
    def test_parseNodeText(self):
        t = '请选择您的$身高$(厘米)?<div></div>输入方式:数值输入框:(50-250)<div>前置业务处理:身高估算<br></div>'
        expexted = {'flag': 'continue','question_content': '请选择您的身高(厘米)?', '主键': '身高', 'question_type': '数值输入框', 'question_limit': '(50-250)', '前置业务处理': '身高估算'}
        a = parseNodeText(t)
        self.assertEquals(a,expexted)
        t = '<div>请输入您孩子的性别？</div><div>输入方式:单选项:男、女<br></div><div>主键:孩子性别</div>'
        a = parseNodeText(t)
        expexted={'flag': 'continue','question_content': '请输入您孩子的性别？', '主键': '孩子性别', 'question_type': '单选项', 'question_option': ['男', '女']}
        self.assertEquals(a,expexted)
        t = '你是否有下列$疾病史$<div></div><div></div>输入方式:多选项:高血压、冠心病、糖尿病、肿瘤、痛风、骨质疏松、不清楚、均没有<div></div>默认值:均没有<br>'
        expexted={'flag': 'continue','question_content': '你是否有下列疾病史', '主键': '疾病史', 'question_type': '多选项', 'question_option': ['高血压', '冠心病', '糖尿病', '肿瘤', '痛风', '骨质疏松', '不清楚', '均没有'], 'default_value': '均没有'}
        a = parseNodeText(t)
        self.assertEquals(a,expexted)

if __name__ == "__main__":
    unittest.main()