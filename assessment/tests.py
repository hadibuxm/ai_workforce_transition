
import re
import json
# Create your tests here.
data = """```json
{
  "readiness_score": 30,
  "time_horizon": "5-8 years",
  "risk_score": 70,
  "recommendation": "The role of this Software Engineer/AI Consultant has a moderate level of automation readiness. Routine coding, testing, and data handling tasks can be partially automated, but highly specialized tasks such as solution architecture design, prompt engineering, research, team leadership, and complex development require human expertise and creativity. Continuous upskilling in AI and ML tools is recommended to stay relevant. Reassessment should occur as AI tools evolve in software development capabilities.",
  "reassessment_time": "3 years",
  "automatable_signals": {
    "routine_coding_tasks": 3,
    "data_management": 2,
    "basic_ml_model_training": 2,
    "testing_and_debugging": 2
  },
  "risk_signals": {
    "solution_architecture_design": 3,
    "prompt_engineering_and_fine_tuning": 3,
    "research_and_development": 3,
    "team_leadership_and_mentoring": 3,
    "complex_web_application_development": 2,
    "creativity_and_innovation": 3
  },
  "duty_sample": [
    "Designing and implementing AI solution architectures for clients",
    "Researching large language models, fine-tuning, and prompt engineering",
    "Developing machine learning models and core wallet microservices",
    "Leading teams and mentoring for software and AI projects",
    "Creating performance testing tools for financial sector projects",
    "Developing applications for real-time data syncing and analytics",
    "Managing full software stack from frontend to backend and databases",
    "Building AI-based platforms involving text and image generation"
  ],
  "resume_excerpt": "AI Consultant providing AI consultancy, designing solution architectures, researching large language models and prompt engineering. Software/ML Engineer with experience in Python, Django, JavaScript, MySQL, building real-time data applications, leading teams, developing AI platforms using large language models and stable diffusion for image generation.",
  "research_insights": [
    "Automation in software development is advancing with AI tools like GitHub Copilot aiding routine coding but not fully replacing experienced engineers in architecture and research tasks.",
    "Prompt engineering and fine-tuning large language models remain specialized roles requiring human judgment and creativity.",
    "Team leadership and complex problem-solving in software projects have low automation potential currently and are critical for project success.",
    "Upskilling in AI and continuous learning are essential for software engineers to leverage automation tools effectively while retaining competitive advantage."
  ]
}
```"""

def extract_and_load_json(text):
    # Regex pattern to match JSON structure
    json_pattern = r'```json\n(\{.*?\})\n```'
    
    # Search for JSON in the provided text
    json_match = re.search(json_pattern, text, re.DOTALL)
    
    if json_match:
        try:
            # Load the matched JSON string into a Python dictionary
            json_data = json.loads(json_match.group(1))  # Corrected to group(1)
            return json_data
        except json.JSONDecodeError:
            print("Error decoding JSON.")
            return None
    else:
        print("No JSON found.")
        return None

# Example usage
sample_text = data
json_result = extract_and_load_json(sample_text)

if json_result:
    print(json_result)