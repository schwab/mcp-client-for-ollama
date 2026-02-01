Take the user observations and design a system that can accomplish the goals.
The user has noticed that many of the ollama models perform well in chat mode and can even answer many questions about software commands starting and stopping services, etc. However, they seem to fail quite often when used to call tools or doing work related to interacting with the operating system or writing software in agent mode.

As a way to move forward and improve the quality of the system in agent mode for olama mCP, the user is contemplating using his chat history as source material for study when it comes to improving the quality of agent mode. How this could work is we could expose many of the chat interactions that are stored on on open web UI to the claude code environment and allow Claude to analyze the chat and compare the results of the o lama agents, the alama chat modes and then come up with a plan for incorporating code changes that can extract the good parts from chat mode and use them to solve agent mode problems.

Claude could become a developer in the middle, essentially running tests against the olama agents and then comparing them to outputs from known chat windows and then finding the strengths that are needed to improve the agent mode and then coming up with a plan to improve the quality for function calling and tool modes.

We also have the tests suite that was built which has prompts that have been tested against the models resulting in grades for the various strengths. We can use this as source knowledge as well. The eventual output would probably be a fine-tuning data set which focuses on the weaknesses of each model and allows us to fine-tune them.

If it's determined that fine tuning is required, we can let Claude work on that as well.

We will let Claude design and interact with the models in whatever way is necessary to allow it to build out the fine-tuning training sets.

In the end we're trying to take the load off of Claude and push as much of the tool calling and easier work down to a llama models which are free to run.