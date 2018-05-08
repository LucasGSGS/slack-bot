#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0301,C0325,C0111

import json
import os
import re
import urllib
import requests

from flask import Flask, request, make_response

COVEO_API_KEY = os.environ.get('COVEO_API_KEY', 'UNDEFINED')
COVEO_SEARCH_PAGE = os.environ.get('COVEO_SEARCH_PAGE', '')

# Flask app should start in global layout
APP = Flask(__name__)


@APP.route('/webhook', methods=['POST'])

def webhook():
    print('request:')
    print(request)
    req = request.get_json(silent=True, force=True)

    res = make_webhook_result(req)
    res = json.dumps(res, indent=4)

    response = make_response(res)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


def get_access_token_params():
    return "&access_token=%s&viewAllContent=1" % COVEO_API_KEY

def create_search_query(search_params):
    return "https://platform.cloud.coveo.com/rest/search/v2?q=" + urllib.quote(search_params.encode('utf-8')) + get_access_token_params()

def send_search_query(query):
    print("Coveo Query: " + query)

    response = requests.request('POST', query)

    if response.status_code == 200:
        response = response.json()
        response['error'] = False
    elif response.status_code == 401:
        response = response_error("Authentication error")
    else:
        response = response_error("Server error")

    return response


def response_template_default(result):
    title = result.get('title', '')
    excerpt = result.get('Excerpt', '')
    uri = result['clickUri']
    uid = result['uniqueId']
    quickview_link = 'https://platform.cloud.coveo.com/rest/search/v2/html?uniqueId=' + urllib.quote(uid) + get_access_token_params()

    attachment = {
        "title": title,
        "title_link": uri,
        "text": "<%s|Quickview>" % quickview_link,
        "color": "#36a64f",

        "fields": [{
            "title": title.encode('utf-8'),
            "value": excerpt.encode('utf-8'),
            "short": "false"
        }]
    }

    return attachment

def response_template_image(result):
    title = result.get('title', '')
    uri = result['clickUri']
    message = {
        "title": title.encode('utf-8'),
        "title_link": uri,
        "color": "#36a64f",
        "image_url": uri
    }
    raw = result['raw']
    if raw and 'awsrekognition' in raw:
        message['fields'] = [{
            "title": "Associated Keywords", "value": ", ".join(raw['awsrekognition'])
        }]

    return message

def add_field(fields, label, raw, attribute):
    if raw and attribute in raw:
        value = re.sub(r'<[^>]*>', '', ', '.join(raw[attribute])) # join values and remove html code
        fields.append({"title": label, "value": value})

def response_template_jsdoc(result):
    uri = result['clickUri']
    raw = result['raw']
    message = {
        "title": raw['jsdoctitle'],
        "title_link": uri,
        "color": "#F58020",
        "footer": "from https://coveo.github.io/search-ui/",
        "footer_icon": "https://s3.amazonaws.com/coveostatic/Developers.png"
    }
    if raw:
        fields = []
        add_field(fields, 'Component Options', raw, 'jsdocoptions')
        add_field(fields, 'Methods', raw, 'jsdocmethods')
        add_field(fields, 'Properties', raw, 'jsdocproperties')

        message['fields'] = fields

        if raw['jsdoctitle']:
            result['title'] = raw['jsdoctitle'] # update title

    return message

def get_icon_for_feature_support(raw, feature_name):
    return ':white_check_mark:' if raw.get(feature_name) == 'true' else ':no_entry_sign:'

def response_template_connector(result):
    uri = result['clickUri']
    raw = result['raw']
    message = {
        "title": raw['vohconnector'],
        "title_link": uri,
        "text": raw['vohversions'],
        "color": "#F58020",
        "footer": "from https://onlinehelp.coveo.com/en/cloud/available_coveo_cloud_v2_source_types.htm",
        "footer_icon": "https://s3.amazonaws.com/coveostatic/OnlineHelp.png"
    }
    if raw:
        # message["text"] = "*Content Update*\n> Refresh :+1:, Rebuild :no_entry_sign:, Rescan :+1:\n*Permission types*\n> Secured :+1:, Private :no_entry_sign:, Shared :+1:"
        fields = []
        fields.append({
            "title": "Content Update",
            "value": "Refresh {0}    |   Rescan {1}   |   Rebuild {2}".format(
                get_icon_for_feature_support(raw, 'vohcanrefresh'),
                get_icon_for_feature_support(raw, 'vohcanrescan'),
                get_icon_for_feature_support(raw, 'vohcanrebuild')
            )
        })
        fields.append({
            "title": "Permission types",
            "value": "Secured {0}    |   Private {1}   |   Shared {2}".format(
                get_icon_for_feature_support(raw, 'vohcansecured'),
                get_icon_for_feature_support(raw, 'vohcanprivate'),
                get_icon_for_feature_support(raw, 'vohcanshared')
            )
        })
        message['fields'] = fields

    return message

def response_empty():
    slack_message = {
        "text": "I couldn't find any result.",
        "attachments": [
            {
                "title": "I am sooooo sorry !!",
                "color": "#f4c242",
                "image_url": "http://icons.iconarchive.com/icons/icons-land/flat-emoticons/128/Cry-icon.png"
            }
        ]
    }
    return {        
        "fulfillmentText": "I couldn't find any result. Sorry.",
        "payload": {"slack": slack_message}
    }

def response_error(err):
    message = "There was an issue with the request. Please contact your administrator. (%s)" % err
    return {        
        "fulfillmentText": message,
        "payload": {
            "slack": {
                "text": message
            }
        }
    }

def response_for_agent(response, slack_message_creator, message, query=None):
    if 'error' in response and response['error']:
        return response

    results = response['results']
    results_len = len(results)

    print("Number of results: %d " % response['totalCount'])

    try:
        if results_len == 0:
            return response_empty()

        top_result = results[0]

        slack_message = {
            "text": "Here is the best match.",
            "attachments": [
                slack_message_creator(top_result)
            ]
        }

        total_count = '%d results' % response['totalCount']
        if query and COVEO_SEARCH_PAGE:
            total_count = '<{0}#q={1}|{2}>'.format(COVEO_SEARCH_PAGE, urllib.quote(query.encode('utf-8')), total_count)

        if results_len > 1:
            slack_message['text'] = 'I found {0}. Here are the two best matches.'.format(total_count)
            slack_message['attachments'].append(slack_message_creator(results[1]))

        title = top_result.get('title', '')
        excerpt = top_result.get('Excerpt', '')

        summary = message.format(title=title.encode('utf-8'), Excerpt=excerpt.encode('utf-8'))

        return {            
            "fulfillmentText": summary,
            "payload": {"slack": slack_message}
        }

    except Exception as any_exception:
        print "Unexpected error:", any_exception
        return response_error(any_exception)

def add_feedback_buttons(response):
    slack = response['payload']['slack']

    if 'attachments' in slack:
        slack['attachments'].append({
            "fallback": "Was it helpful?",
            "title": "Was it helpful?",
            "callback_id": "feedback_ua",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [{
                "name": "helpful",
                "text": "Yes",
                "type": "button",
                "style": "primary",
                "value": "yes"
            }, {
                "name": "helpful",
                "text": "No",
                "type": "button",
                "style": "danger",
                "value": "no"
            }]
        })

    return response


def make_webhook_result(req):
    print 'Req:'
    print req

    result = req.get("queryResult")
    parameters = result.get("parameters")
    searchterms = parameters.get("any")
    contentsource = parameters.get("contentSource", '')
    timeframe = parameters.get("date-time", '')

    intenttype = result.get("intent").get("displayName")

    print('My Intent: "%s"' %  intenttype)

    if intenttype == "findimage":
        query = create_search_query("@awsrekognition==%s" % searchterms)
        response = send_search_query(query)

        return response_for_agent(response, response_template_image, "The top result is: {title}")

    elif intenttype == "showdoc":
        query = create_search_query("@jsdoctitle==%s" % searchterms)
        response = send_search_query(query)

        return response_for_agent(response, response_template_jsdoc, "The top result is: {title}")

    elif intenttype == "versionsForConnector":
        query = create_search_query('@vohconnector=%s and @uri in ("https://onlinehelp.coveo.com/en/cloud/add_edit_amazon_s3_source.htm.splid" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Box_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/add_edit_confluence_legacy_source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Confluence_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Confluence_Cloud_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Drive_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Drive_for_Work_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Dropbox_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Exchange_Online_Personal_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Gmail_Personal_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Gmail_for_Work_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_JIRA_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_JIRA_Cloud_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Jive_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Jive_Cloud_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Lithium_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Push_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_RSS_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Salesforce_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_SharePoint_Online_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Sitecore_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Sitemap_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_Web_Source.htm" OR "https://onlinehelp.coveo.com/en/cloud/Add_Edit_YouTube_Source.htm")' % parameters.get("connector"))
        response = send_search_query(query)

        return response_for_agent(response, response_template_connector, "The top result is: {title}")


    elif intenttype == "UserMakesQuery - yes":
        print('TODO: send YES to UA event...')
        return {            
            "fulfillmentText": "Great!",
            "payload": {
                "slack": {
                    "response_type": "ephemeral",
                    "replace_original": True,
                    "text": "Great!"
                }
            }
        }

    elif intenttype == "UserMakesQuery - no":
        print('TODO: send NO to UA event...')
        return {
            "fulfillmentText": "Okay.",
            "payload": {
                "slack": {
                    "response_type": "ephemeral",
                    "replace_original": True,
                    "text": "Okay."
                }
            }
        }

    else:
        print "source: %s" % contentsource
        if contentsource:
            contentsource = ' AND @syssource="%s"' % contentsource

        print "timeframe: %s" % timeframe
        timeframe = timeframe.split('/')[0]
        timeframe = timeframe.replace('-', '/') # API.ai uses format 2017-06-15 and Coveo 2017/06/15
        if timeframe:
            timeframe = " AND @date>=" + timeframe

        query = ''.join((searchterms, contentsource, timeframe))
        response = send_search_query(create_search_query(query))

        response = response_for_agent(response, response_template_default, "The top result is: {title}\nThe summary is: \n{Excerpt}", query)
        if 'Sorry.' not in response["fulfillmentText"]:
            add_feedback_buttons(response)

        return response

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 5000))

    print "Starting app on port %d" % PORT

    APP.run(debug=True, port=PORT, host='0.0.0.0')
