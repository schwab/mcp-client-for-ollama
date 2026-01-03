
## Done 
  - Clean Nextcloud-blue interface
  - Properly formatted markdown responses
  - Multi-line prompts with Shift+Enter
  - Real-time agent activity tracking

## PHASE 1
     - remove the text of shift+enter prompt from the chat ui input box
     - agent activity and tools should both be collapsable at the same level.
     - agent activity should not be inside the tools box these are different seperate functions
     - remove . and _ from tool names displayed to user (make them more user freindly) but keep them correct for the tool itself
     - highlight tools that were recently called by the agents making tool usage more apparent
     - implement reload-servers function in the UI (create a button bar)


## PHASE 2
     - create a dockerfile for installing the tool on a server
     - expose the app folder via a docker volume so changes to config are persisted and .trace files are accesible