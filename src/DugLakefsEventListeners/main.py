import json
import logging
import os
import requests

from flask import Flask, request, jsonify

INVOKE_AIRFLOW_WITH_DIFF = "invoke_airflow_with_diff"
RELAY = "relay"
AIRFLOW_URL = "http://127.0.0.1:8080/api/v2/"
AIRFLOW_AUTH_URL = "http://127.0.0.1:8050/auth/token"
app = Flask(__name__)


def airflow_token():
    logging.info("Getting token")
    r = requests.post(AIRFLOW_AUTH_URL,
                      json={"username": os.environ["AIRFLOW_USER"],
                            "password": os.environ["AIRFLOW_PASSWORD"]},
                      timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def invoke_airflow_dag(dag_id, repository_id, branch_name, last_commit_id, new_commit_id, commit_id) -> tuple:

    if commit_id:
        params = \
            {
                "logical_date": None,
                'conf':
                      {
                          'source': 'lakefs',
                          'repository_id': repository_id,
                          'branch_name': branch_name,
                          'commit_id' : commit_id
                      }
            }
    else:
        params = \
            {
                "logical_date": None,
                'conf':
                    {
                        'source': 'lakefs',
                        'repository_id': repository_id,
                        'branch_name': branch_name,
                        'commitid_from' : last_commit_id,
                        'commitid_to' : new_commit_id
                    }
            }

    url = AIRFLOW_URL + f"dags/{dag_id}/dagRuns"
    headers = {"Authorization": f"Bearer {airflow_token()}"}

    logging.info("Calling Airflow DAG {}".format(dag_id))
    logging.info("Url: {}".format(url))
    logging.info("Params: {}".format(params))
    resp = requests.post(url, headers=headers, json=params, timeout=120)
    logging.info(resp)

    if resp.status_code not in (200, 201, 409):
        return (False, resp.json())
    else:
        return (True, None)


@app.route('/' + INVOKE_AIRFLOW_WITH_DIFF, methods=["POST"])
def invoke_airflow_with_diff():
    input_data = request.json
    logging.info(INVOKE_AIRFLOW_WITH_DIFF)
    logging.info(input_data)

    config = {}
    config_json = f"./data/{INVOKE_AIRFLOW_WITH_DIFF}_config.json"

    if not os.path.isfile(config_json):
        logging.error(f"{config_json} not found!")
        output_data = {'status': 'error'}
        return jsonify(output_data)

    with open(config_json, "r") as f:
        config = json.load(f)

    repository_id = input_data["repository_id"]
    source_ref = input_data["source_ref"]

    dags = config["dags"]

    for dag in dags:
        if dag["repository_id"] == repository_id:
            res, body = invoke_airflow_dag(dag["dag_id"], repository_id, dag["branch_name"], dag["last_commit_id"], source_ref, None)
            if res:
                dag["last_commit_id"] = source_ref
                with open(config_json, "w") as f:
                    json.dump(config, f, indent=4)

                output_data = {'status': 'OK'}
            else:
                output_data = {'status': 'error', 'error' : body}

    return jsonify(output_data)


@app.route('/' + RELAY, methods=["POST"])
def relay():
    input_data = request.json
    logging.info(RELAY)
    logging.info(input_data)

    dag_id = request.args.get("dag_id")
    repository_id = input_data["repository_id"]
    source_ref = input_data["source_ref"]
    branch_name = input_data["branch_id"]
    commit_id = input_data["commit_id"]

    res, body = invoke_airflow_dag(dag_id, repository_id, branch_name, None, None, commit_id)

    if res:
        output_data = {'status': 'OK'}
    else:
        output_data = {'status': 'error', 'error' : body}

    return jsonify(output_data)

if __name__ == '__main__':
    logging.basicConfig(filename='logs.log', level=logging.DEBUG, format="%(asctime)s:%(levelname)s: %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler())
    AIRFLOW_URL = os.environ.get("AIRFLOW_URL", AIRFLOW_URL)
    AIRFLOW_AUTH_URL = os.environ.get("AIRFLOW_AUTH_URL", AIRFLOW_AUTH_URL)
    app.debug = True
    app.run(host='0.0.0.0', port=8001)

    # app.run(host=os.getenv("HOST", "127.0.0.1"),
    #         port=8001,
    #         debug=os.getenv("FLASK_DEBUG") == "1",
    #         use_reloader=False)