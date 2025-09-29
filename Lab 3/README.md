# Chatterboxes
**NAMES OF COLLABORATORS HERE**
[![Watch the video](https://user-images.githubusercontent.com/1128669/135009222-111fe522-e6ba-46ad-b6dc-d1633d21129c.png)](https://www.youtube.com/embed/Q8FWzLMobx0?start=19)

In this lab, we want you to design interaction with a speech-enabled device--something that listens and talks to you. This device can do anything *but* control lights (since we already did that in Lab 1).  First, we want you first to storyboard what you imagine the conversational interaction to be like. Then, you will use wizarding techniques to elicit examples of what people might say, ask, or respond.  We then want you to use the examples collected from at least two other people to inform the redesign of the device.

We will focus on **audio** as the main modality for interaction to start; these general techniques can be extended to **video**, **haptics** or other interactive mechanisms in the second part of the Lab.



\*\***Write your own shell file to use your favorite of these TTS engines to have your Pi greet you by name.**\*\*
(This shell file should be saved to your own repo for this lab.)



\*\***Write your own shell file that verbally asks for a numerical based input (such as a phone number, zipcode, number of pets, etc) and records the answer the respondent provides.**\*\*



\*\***Try creating a simple voice interaction that combines speech recognition, Ollama processing, and text-to-speech output. Document what you built and how users responded to it.**\*\*

### Storyboard

 I am making a device that can act as a psycologist or someone with whom i can just talk to when I am frustrated or stressed. 

\*\***Post your storyboard and diagram here.**\*\*

<img width="511" height="388" alt="image" src="https://github.com/user-attachments/assets/267f52a3-bb55-484c-8881-fdf887265657" />
 

Different Scenarios:

**Scenario 1:**
User Input: "I am so annoyed right now."

Chatbot Response: "I hear you. It's completely valid to feel that way. What's on your mind? Sometimes just talking about it can help."

User Input: "My coworker keeps interrupting me in meetings."

Chatbot Response: "That sounds incredibly frustrating. When you feel a surge of annoyance, what's a small step you can take for yourself? For example, you can take a moment for yourself, even if it's just a few seconds."

User Input: "I just don't know what to do."

Chatbot Response: "That's okay. You don't have to have all the answers right now. Let's just focus on one thing. How would you like to feel instead of annoyed?"

Follow-Up: The chatbot could then offer suggestions like practicing a breathing exercise, journaling about the frustration, or even creating a plan for how to address the coworker.

**Scenario 2:**
User Input: "I feel really down and lonely."

Chatbot Response: "I'm so sorry to hear that. It takes a lot of courage to admit that you're struggling. What's one thing you'd like to talk about right now?"

User Input: "I just miss my friends. I haven't seen them in a while."

Chatbot Response: "That makes perfect sense. It's tough when you can't connect with the people you care about. When you miss them, what's a happy memory you have with them?"

User Input: "We went on a road trip last year and it was so much fun."

Chatbot Response: "That's wonderful! It sounds like a cherished memory. Is there a small way you could connect with them today, even if it's just a quick text or a call?"

Follow-Up: The chatbot could offer other ideas, such as listening to music that reminds them of their friends, looking at old photos, or planning a time to meet in the future.

**Scenario 3:**
User Input: "I am so worried about my job interview tomorrow. I can't stop thinking about everything that could go wrong."

Chatbot Response: "It sounds like you're carrying a lot of worry right now. That's a heavy feeling. Let's try to focus on one thing at a time. What's one small detail you are prepared for?"

User Input: "I've practiced my answers for a lot of the common questions."

Chatbot Response: "That's fantastic! You've already taken an important step and prepared yourself. That's something to be proud of. Let's try a quick grounding exercise. Name five things you can see right now."

User Input: "A lamp, my notebook, a cup of coffee, a window, my phone."

Chatbot Response: "Good. Now, what's one simple thing you can do right now to help yourself feel a bit more at ease?"

Follow-Up: The chatbot could suggest taking a walk, listening to a calming podcast, or writing down a list of things that could go right in the interview to shift their perspective.

\*\***Please describe and document your process.**\*\*

### Acting out the dialogue

Find a partner, and *without sharing the script with your partner* try out the dialogue you've designed, where you (as the device designer) act as the device you are designing.  Please record this interaction (for example, using Zoom's record feature).

\*\***Describe if the dialogue seemed different than what you imagined when it was acted out, and how.**\*\*

### Wizarding with the Pi (optional)
In the [demo directory](./demo), you will find an example Wizard of Oz project. In that project, you can see how audio and sensor data is streamed from the Pi to a wizard controller that runs in the browser.  You may use this demo code as a template. By running the `app.py` script, you can see how audio and sensor data (Adafruit MPU-6050 6-DoF Accel and Gyro Sensor) is streamed from the Pi to a wizard controller that runs in the browser `http://<YouPiIPAddress>:5000`. You can control what the system says from the controller as well!

\*\***Describe if the dialogue seemed different than what you imagined, or when acted out, when it was wizarded, and how.**\*\*

# Lab 3 Part 2

For Part 2, you will redesign the interaction with the speech-enabled device using the data collected, as well as feedback from part 1.

## Prep for Part 2

1. What are concrete things that could use improvement in the design of your device? For example: wording, timing, anticipation of misunderstandings...
2. What are other modes of interaction _beyond speech_ that you might also use to clarify how to interact?
3. Make a new storyboard, diagram and/or script based on these reflections.

## Prototype your system

The system should:
* use the Raspberry Pi 
* use one or more sensors
* require participants to speak to it. 

*Document how the system works*

*Include videos or screencaptures of both the system and the controller.*

<details>
  <summary><strong>Submission Cleanup Reminder (Click to Expand)</strong></summary>
  
  **Before submitting your README.md:**
  - This readme.md file has a lot of extra text for guidance.
  - Remove all instructional text and example prompts from this file.
  - You may either delete these sections or use the toggle/hide feature in VS Code to collapse them for a cleaner look.
  - Your final submission should be neat, focused on your own work, and easy to read for grading.
  
  This helps ensure your README.md is clear professional and uniquely yours!
</details>

## Test the system
Try to get at least two people to interact with your system. (Ideally, you would inform them that there is a wizard _after_ the interaction, but we recognize that can be hard.)

Answer the following:

### What worked well about the system and what didn't?
\*\**your answer here*\*\*

### What worked well about the controller and what didn't?

\*\**your answer here*\*\*

### What lessons can you take away from the WoZ interactions for designing a more autonomous version of the system?

\*\**your answer here*\*\*


### How could you use your system to create a dataset of interaction? What other sensing modalities would make sense to capture?

\*\**your answer here*\*\*







