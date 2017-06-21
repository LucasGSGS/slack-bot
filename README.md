# Coveo integration with Slack

This project describes how to integrate Coveo within Slack to create a search (chat) bot.

It uses multiple components:
* __Coveo platform__ - hosts the index and organization for your data, provides the search capabilities.
* __Heroku__ - hosts the webhook API.ai will send the intents to and queries Coveo.
* __Slack__ - the application users will use to interact with Coveo. It will be like doing a conversation with a user in Slack.
* __API.ai__ - Process the queries from Slack and translate them to Intents.

## How it works

In Slack, users send queries to user `@coveo` like `@coveo search for JavaScript framework`. Or they can have direct messages with `@coveo`.
Slack will send the message to API.ai which will transform it to an User Intent.
API.ai sends the Intent to the Heroky app which will send a query to Coveo based on the keywords in the intent.
The results are returned to Slack.

## How to build

### Coveo

1. In your Coveo organization, create a hosted search page to show _more results_ from Slack.

### Heroku

1. Set up a new project in [Heroku](https://dashboard.heroku.com)
   * Add the files from `misc/heroku` in your Heroku environment.
   * Add config variable `COVEO_API_KEY` with your Coveo API key.
   * Add config variable `COVEO_SEARCH_PAGE` with the url to the Search Page for the _results_ link in Slack.
   * Start your app in Heroku

1. Set up your `COVEO_API_KEY` as a config variable in your Heroku app
1. Start your app in Heroku
  a. create a new Heroku app
  b. wait for the app status' to be "ready"
1. In API.ai, create an agent and follow the procedure in API.ai's [Slack Integration](https://docs.api.ai/docs/slack-integration).

### API.ai

1. In [API.ai](https://console.api.ai/api-client) console, create a new agent.
1. You can import the file `misc/api.ai/agent.config.zip` to reproduce our intents.
1. Go in _Fulfillment_ and update the URL to your Heroku app.
1. Go in _Integration_ and enable Slack. Follow the instructions to connection to your Slack app.

### Slack

1. You need to create a new App. Follow the instructions at https://api.slack.com/apps?new_app=1

## How to run

Once you've completed your Slack integration, you can send direct messages to your new bot in Slack. You can send messages like `find images with dinosaurs`.

## Dependencies

- You will need a [Coveo organization](https://platform.cloud.coveo.com) and an Api key (restricted to Search only).
- __Heroku__, this application is hosted in Heroku.
- __API.ai__, this application uses services from API.ai, you can register for a free account.
- __Slack__, we are creating a slack bot, so you need Slack ;o)

## References

- [Coveo Search API](https://developers.coveo.com/display/CloudPlatform/Search+API)
- [Slack Integration how-to](https://docs.api.ai/docs/slack-integration)
- [Slack + Webhook Integration Example from API.ai](https://docs.api.ai/docs/slack-webhook-integration-guideline)
-

## Authors

- Gauthier Robe (https://github.com/gforce81)
- Jérôme Devost (https://github.com/jdevost)
