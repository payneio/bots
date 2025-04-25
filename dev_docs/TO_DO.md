# Bots Project: TO DO
- [ ] Be able to interrupt the bot with ESC
- [ ] Add 'name' and 'emoji' to config.json
- [ ] Instead of just approve/deny, also ask for 'approve in session', and 'approve all time'... number the options.
- [ ] With 'bots init <bot> --description <description>', instead of just initializing a copy of the template, use the template to create a new bot with a revised system_prompt and config.json that matches the intent given in the description.
- [ ] Move most non-cli functionality into a library.
- [ ] Interbot communication. Design thoughts: A bot should have a tool that allows it to start a separate session of itself that can drive a chat with another bot; Starts with a goal (the first message to the partner bot, but also a concatenation to the system prompt); Drives towards that goal via system prompt until calling a FINISH tool; Only a summary of the conversation is preserved in the launchers chat history (created with the FINISH tool); have a max_steps that is given on session start and maintained in the system prompt.
- [ ] Allow conversation given to a bot via stdin when starting up.
- [ ] sub-bots. Design thoughts: Bots stored in a bot directory that can only be run by that bot; enables separate conversation threads.
- [ ] bot bin scripts. Design thoughts: a type of procedural memory; MAKE_SCRIPT (command?) tool; It makes it in config/bin, makes it executable, and adds a description to README; The README is ...
