#import pygraphviz as pgv
import pydot
import json
from tetpyclient import RestClient
import requests.packages.urllib3
import csv

API_ENDPOINT="https://medusa-cpoc.cisco.com"
API_CREDS="/Users/christophermchenry/Documents/Scripting/tetration-api/medusa_credentials.json"

def selectTetrationApps(endpoint,credentials):

    restclient = RestClient(endpoint,
                            credentials_file=credentials,
                            verify=False)

    requests.packages.urllib3.disable_warnings()
    resp = restclient.get('/openapi/v1/applications')

    if not resp:
        sys.exit("No data returned for Tetration Apps! HTTP {}".format(resp.status_code))

    app_table = []
    app_table.append(['Number','Name','Author','Primary'])
    print('\nApplications: ')
    for i,app in enumerate(resp.json()):
        app_table.append([i+1,app['name'],app['author'],app['primary']])
        print ('%i: %s'%(i+1,app['name']))
#    print(AsciiTable(app_table).table)
    choice = raw_input('\nSelect Tetration App: ')

    choice = choice.split(',')
    appIDs = []
    for app in choice:
        if '-' in app:
            for app in range(int(app.split('-')[0]),int(app.split('-')[1])+1):
                appIDs.append(resp.json()[int(app)-1]['id'])
        else:
            appIDs.append(resp.json()[int(app)-1]['id'])

    return appIDs

def main():
    """
    Main execution routine
    """
    protocols = {}
    try:
        with open('protocol-numbers-1.csv') as protocol_file:
            reader = csv.DictReader(protocol_file)
            for row in reader:
                protocols[row['Decimal']]=row
    except IOError:
        print '%% Could not load protocols file'
        return
    except ValueError:
        print 'Could not load improperly formatted protocols file'
        return

    appIDs = selectTetrationApps(endpoint=API_ENDPOINT,credentials=API_CREDS)

    showPorts = raw_input('\nWould you like to include ports and protocols in the diagram? [Y,N]: ')

    if showPorts.upper() == 'Y':
        showPorts = True
    elif showPorts.upper() == 'N':
        showPorts = False
    else:
        print('Invalid input.')
        return


    restclient = RestClient(API_ENDPOINT,credentials_file=API_CREDS,verify=False)

    for appID in appIDs:
        print appID
        appDetails = restclient.get('/openapi/v1/applications/%s/details'%appID).json()

        with open('./SQL-DVA-v8-policies.json') as config_file:
            appDetails = json.load(config_file)

        #graph = pgv.AGraph(directed=True, rankdir="LR", name=appDetails['name'])
        graph = pydot.Dot(graph_type='digraph',name=appDetails['name'])
        print('\nPreparing "%s"...'%appDetails['name'])
        for cluster in appDetails['clusters']:
            node_names = cluster['name'] + ':'
            for node in cluster['nodes']:
                node_names = node_names + '\n' + node['name']
            #graph.add_node(cluster['id'],
            #                    label=node_names)
            graph.add_node(pydot.Node(cluster['id'],label=node_names))
        for invfilter in appDetails['inventory_filters']:
            #graph.add_node(invfilter['id'],
            #                    label=invfilter['name'],style='filled', color='lightblue')
            graph.add_node(pydot.Node(invfilter['id'],label='"'+invfilter['name']+'"',style='filled', fillcolor='lightblue'))
        for policy in appDetails['default_policies']:

            if showPorts:
                policies = {}
                #Sort ports and protocols
                for port_range in policy['l4_params']:

                    if port_range['port'][0] == port_range['port'][1]:
                        port = str(port_range['port'][0])
                    else:
                        port = str(port_range['port'][0]) + '-' + str(port_range['port'][1])

                    if protocols[str(port_range['proto'])]['Keyword'] in policies.keys():
                        policies[protocols[str(port_range['proto'])]['Keyword']].append(port)
                    else:
                        policies[protocols[str(port_range['proto'])]['Keyword']] = [port]

                #Stringify policies
                ports = '\n'.join("%s=%r" % (key,val) for (key,val) in policies.iteritems())
                ports = policy['consumer_filter_name'] + '-->' + policy['provider_filter_name'] + ':\n' + ports
                #pol_node = graph.add_node(policy['consumer_filter_id']+policy['provider_filter_id'],
                #                    label=ports, shape='box',
                #                    style='filled', color='lightgray')
                pol_node = graph.add_node(pydot.Node(policy['consumer_filter_id']+policy['provider_filter_id'],
                                    label=ports, shape='box',
                                    style='filled', color='lightgray'))
                #graph.add_edge(policy['consumer_filter_id'],policy['consumer_filter_id']+policy['provider_filter_id'])
                #graph.add_edge(policy['consumer_filter_id']+policy['provider_filter_id'],policy['provider_filter_id'])
                graph.add_edge(pydot.Edge(policy['consumer_filter_id'],policy['consumer_filter_id']+policy['provider_filter_id']))
                graph.add_edge(pydot.Edge(policy['consumer_filter_id']+policy['provider_filter_id'],policy['provider_filter_id']))

            else:
                if policy['consumer_filter_id'] == '5959528c755f024cb6d32189' and policy['provider_filter_id'] == '5959528c755f024cb6d3218c':
                    print('I think this is right')
                graph.add_edge(pydot.Edge(policy['consumer_filter_id'],policy['provider_filter_id']))

        f = open(appDetails['name']+'.dot','w')
        #f.write(graph.string())
        f.write(graph.to_string())
        #print(graph.string())

if __name__ == '__main__':
    main()
