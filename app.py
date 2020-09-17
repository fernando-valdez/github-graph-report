#!/usr/bin/env python3
#
# Lists the assigned open pull issues at https://github.com/oracle/graal 
#

import sys, os, argparse, json, urllib.request
from datetime import datetime
from pytablewriter import MarkdownTableWriter  # pip3 install pytablewriter

token = os.environ.get("GITHUB_TOKEN")
data = {}
team_total_assigned = 0
team_total_closed = 0

# Date from last release
release_date = datetime(2020, 9, 2) 

# List of team members
team = {"fernando-valdez", "jramirez-isc","mcraj017", "oubidar-Abderrahim","amine-arb-2019" }

if token is None:
    raise SystemExit("Set GITHUB_TOKEN environment variable to specify your GitHub personal access token (https://github.com/settings/tokens)")
headers = {"Authorization": "Bearer " + token}

def run_query(query):
    req = urllib.request.Request(url='https://api.github.com/graphql', data=json.dumps({'query' : query}).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as f:
        if f.status == 200:
            result = f.read().decode('utf-8')
            return json.loads(result)
        else:
            raise Exception("Query failed to run by returning code of {}. {}".format(f.status, query))


def get_open_nodes_query_by_user(node_type, cursor=None):
    after = ', after: "{}"'.format(cursor) if cursor is not None else ''
    return """
{
  repositoryOwner(login: "oracle") {
    repository(name: "graal") {
      """ + node_type + """s(first: 100, """ + after + """) {
        totalCount
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            number
            url
            state
            createdAt
            title
            assignees(first: 1) {
              totalCount
              edges {
                node {
                  login
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

def print_nodes_mark_down(node_type, nodes):
    writer = MarkdownTableWriter()

    writer.headers = ['ID', 'Link to GitHub', "Created date", "Status",  'Title', 'Assigned to']

    writer.value_matrix = filter_nodes_data(node_type, nodes)

    print(writer.dumps())

def filter_nodes_data(node_type, nodes):
    return [[node[1]["number"], node[1]["url"], node[1]["createdAt"], node[1]["state"],  node[1]["title"][0:100], node[1]["assignees"]["edges"][0]["node"]["login"]] for node in sorted(nodes.items())]

def get_nodes(node_type):
    all_nodes = {}
    endCursor = None
    sys.stdout.write("Getting " + node_type + "s")
    sys.stdout.flush()
    while True:
        sys.stdout.write(".")
        sys.stdout.flush()
        result = run_query(get_open_nodes_query_by_user(node_type, endCursor))
        nodes = result["data"]["repositoryOwner"]["repository"][node_type + "s"]
        edges = nodes["edges"]
        for e in edges:
            node = e["node"]
            all_nodes[node["number"]] = node
        page_info = nodes["pageInfo"]
        if page_info["hasNextPage"] != True:
            break
        else:
            endCursor = page_info["endCursor"]
    sys.stdout.write(os.linesep)
    sys.stdout.flush()
    return all_nodes 

def show_unassigned_nodes(node_type):
    global data
    if not data:
      data = get_nodes(node_type)
    total_unassigned = 0
    unassigned_nodes = {}
    for _, node in sorted(data.items()):
        num_assignees = int(node["assignees"]["totalCount"])
        if num_assignees == 0:
            unassigned_nodes[node["number"]] = node
            total_unassigned += 1
    print("Total unassigned open " + node_type + "s: " + str(total_unassigned))
    print_nodes_mark_down(node_type, unassigned_nodes)

def show_assigned_nodes(node_type, assignee):
    global data
    global team_total_assigned
    global team_total_closed
    if not data:
      data = get_nodes(node_type)
    total_assigned = 0
    assigned_nodes = {}
    for _, node in sorted(data.items()):
        num_assignees = int(node["assignees"]["totalCount"])

        if num_assignees > 0: 
          node_date = datetime.strptime(node["createdAt"],'%Y-%m-%dT%H:%M:%SZ')

          if node_date>=release_date:
            assignee_nodes = node["assignees"]["edges"]

            if assignee_nodes[0]["node"]["login"] == assignee:
              assigned_nodes[node["number"]] = node
              total_assigned += 1

              if node["state"] =="CLOSED":
                team_total_closed+=1

    team_total_assigned +=total_assigned
    print("Total open " + node_type + "s assigned to " + assignee +": " + str(total_assigned))
    print_nodes_mark_down(node_type, assigned_nodes)

def main():
    p = argparse.ArgumentParser()
    p.parse_args()

    for member in team:
      show_assigned_nodes('issue', member)

    print("Github Issues handled by support: " + str(team_total_assigned))
    print("Github Issues closed by support: " + str(team_total_closed))

main()
