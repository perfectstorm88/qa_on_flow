import requests

a =  {
  "question_seq":"",
  "question_anwser":"",
  "all_anwser":{},
  "flow_name":"健康APP引导流程"
}
a = requests.post('http://0.0.0.0:6012/api/p/qa', json=a)
print(a.json())
print(a.text)