### Prompt Engineering Concepts

Use this file to explain 3 different prompt engineering concepts that you tried and their effectiveness. You can include screenshots of your prompts and the AI's responses if you like.
# Prompt Engineering Concepts & Effectiveness

In this assignment, three main prompt engineering techniques were implemented and evaluated to optimize expert responses and routing.

## 1. System Prompting & Role Specification
* **Concept:** Assigning a highly specific identity and strict boundary instructions to the model (e.g., specifying that the model is a "Database Read Expert").
* **Effectiveness:** Highly effective. It prevented the LLM from engaging in conversational filler and forced it to output pure SQL queries, making parsing seamless.

## 2. Dynamic Template Filling (Master Template Pattern)
* **Concept:** Using a unified structure (`master_template`) that dynamically injects the role, instructions, context, and query at runtime.
* **Effectiveness:** Very effective in maintaining consistency across different agents (Read, Write, and Content experts) while reducing code redundancy.

## 3. Chain-of-Thought / Sequential Planning (Orchestrator Pattern)
* **Concept:** Instructing the LLM Orchestrator to break down complex queries into a structured 2-step plan before execution.
* **Effectiveness:** Essential for handling compound requests (e.g., checking if a skill exists first, and inserting it if missing). It dramatically improved multi-step execution reliability.