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
I acted out the dialogue with Jesse Iriah (ji227)

https://drive.google.com/file/d/1WoFmKKsMylO-HeaHTgoi1JtIKU5Nhr9m/view?usp=drive_link 

\*\***Describe if the dialogue seemed different than what you imagined when it was acted out, and how.**\*\*
The dialogue was much more casual than what I imagined it to be. The user also took some time to answer some of the questions.
The chatbot had to ask a lot of follow up questions in order to help the user. For example, the user said that they were very overwhelmed 
their studies. The chatbot had to follow up with a question about how they are dealing with these feelings. What are they doing to help relax themselves.


# Lab 3 Part 2

For Part 2, you will redesign the interaction with the speech-enabled device using the data collected, as well as feedback from part 1.

## Prep for Part 2

1. What are concrete things that could use improvement in the design of your device? For example: wording, timing, anticipation of misunderstandings...
2. What are other modes of interaction _beyond speech_ that you might also use to clarify how to interact?
3. Make a new storyboard, diagram and/or script based on these reflections.

## Prototype your system

[Code for Chatbot](voice_assistant.py)

**Hardware components**
Raspberry Pi with Mini PiTFT display (240x135 ST7789)
Push button (GPIO 23) for recording control
Speaker for audio output
Microphone for voice input

**Software Stack**

Vosk: Offline speech recognition (converts speech to text)
Ollama + TinyLlama: Local AI model for generating conversational responses
Piper: Text-to-speech synthesis (converts text to spoken audio)
Python libraries: sounddevice, PIL, adafruit_rgb_display

**How it works**
User presses button → microphone captures audio → Vosk transcribes to text → TinyLlama generates response → Piper converts to speech → audio plays through speaker. The display shows animated faces (idle/listening/thinking/speaking) to provide visual feedback throughout the interaction cycle.

**Key Features**
Visual Feedback: Four face states (idle, listening, thinking, speaking) provide clear user feedback
Button-Based Recording: Push-to-talk prevents false triggers and gives users control over recording boundaries
Brief Responses: AI constrained to 1-2 sentences to maintain engagement in voice conversations
Error Handling: Fallback responses and exception handling ensure robust operation

*Include videos or screencaptures of both the system and the controller.*


## Test the system
Try to get at least two people to interact with your system. (Ideally, you would inform them that there is a wizard _after_ the interaction, but we recognize that can be hard.)

Answer the following:

### What worked well about the system and what didn't?
The conversation with the chatbot was very robotic and scripted. The chat bot wasnt able to give more personalized replies.

### What worked well about the controller and what didn't?

Initially, the chatbot would talk over me when I would take some time to reply. However, I added a new feature where I can press a button, speak and then press the button again. This way, the chatbot knows when I start and stop speaking.

### What lessons can you take away from the WoZ interactions for designing a more autonomous version of the system?
1. The WoZ interactions reveal that natural conversation requires context awareness. An autonomous system needs robust conversation memory (like your conversation_history) to maintain coherent multi-turn dialogues and avoid repetitive responses.
2. The constraint to keep AI responses to 1-2 sentences is crucial - users lose engagement with lengthy responses in voice interactions. This differs significantly from text-based chat.
3. The physical button for recording boundaries reduces false triggers but creates a less natural interaction pattern. A fully autonomous system would benefit from wake word detection or voice activity detection for more seamless conversations.

### How could you use your system to create a dataset of interaction? What other sensing modalities would make sense to capture?
We can do the following:
- Response Quality Metrics: Track which AI responses led to continued conversation vs. premature exits
- Button Press Patterns: Record timing between button presses to understand how users structure their speaking turns

Additional Sensors that can be implemented:
- Camera : Can be used for face detection. We can train a model to recognize emotions.
- Proximity Sensor: Detect when users approach/leave to automatically wake or sleep the system








