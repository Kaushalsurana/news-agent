import streamlit as st
from datetime import datetime, timedelta
import os
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable EntityMemory before importing crewai
os.environ['CREWAI_DISABLE_ENTITY_MEMORY'] = 'true'

try:
    from crewai import Agent, Crew, Process, Task
    from crewai.project import CrewBase, agent, crew, task
    from langchain_openai import ChatOpenAI
    import litellm
    from search_tools import SearchTools
except ImportError as e:
    st.error(f"Failed to import required modules: {str(e)}")
    st.info("Please make sure all required packages are installed. Check the requirements.txt file.")
    st.stop()

def get_api_key(key_name, display_name):
    key = st.sidebar.text_input(f"Enter your {display_name}", type="password")
    if not key:
        st.sidebar.warning(f"{display_name} is required.")
    return key

def initialize_openai_chat(model_name):
    api_key = st.session_state.get('OPENAI_API_KEY')
    if not api_key:
        st.sidebar.error("OpenAI API Key is missing.")
        return None
    os.environ['OPENAI_API_KEY'] = api_key  # Set the environment variable
    litellm.api_key = api_key  # Set the API key for litellm
    return ChatOpenAI(api_key=api_key, model=model_name)

def streamlit_callback(step):
    if hasattr(step, 'get'):
        agent = step.get('agent', 'Unknown Agent')
        task = step.get('task', 'Unknown Task')
        status = step.get('status', 'No Status')
        output = step.get('output', '')
    else:
        agent = getattr(step, 'agent', 'Unknown Agent')
        task = getattr(step, 'tool', 'Unknown Task')
        status = "In Progress"
        output = getattr(step, 'tool_input', '')
    
    st.markdown(f"**{agent}**: {task}")
    st.markdown(f"_{status}_")
    if output:
        st.text(output)
    st.markdown("---")
    logger.info(f"Agent: {agent}, Task: {task}, Status: {status}, Output: {output}")

@CrewBase
class TopicNewsCrew():
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(current_dir, 'config')
        agents_path = os.path.join(config_dir, 'agents.yaml')
        tasks_path = os.path.join(config_dir, 'tasks.yaml')
        
        try:
            with open(agents_path, 'r') as f:
                self.agents_config = yaml.safe_load(f)
            with open(tasks_path, 'r') as f:
                self.tasks_config = yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            st.error(f"Configuration file not found: {e}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            st.error(f"Error parsing YAML file: {e}")
    
    @agent
    def news_fetcher_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['news_fetcher_agent'],
            tools=[SearchTools()],
            verbose=True,
            allow_delegation=False,
            step_callback=streamlit_callback,
            max_iter=1,
            llm=initialize_openai_chat("gpt-3.5-turbo")
        )
    
    @agent
    def news_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['news_analyzer_agent'],
            verbose=True,
            allow_delegation=False,
            step_callback=streamlit_callback,
            max_iter=1,
            llm=initialize_openai_chat("gpt-3.5-turbo")
        )
    
    @task
    def fetch_topic_news_task(self) -> Task:
        return Task(
            config=self.tasks_config['fetch_topic_news_task'],
            agent=self.news_fetcher_agent(),
            output_file="fetched_topic_news.md"
        )
    
    @task
    def analyze_topic_news_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_topic_news_task'],
            agent=self.news_analyzer_agent(),
            output_file="analyzed_topic_news.md"
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.news_fetcher_agent(),
                self.news_analyzer_agent()
            ],
            tasks=[
                self.fetch_topic_news_task(),
                self.analyze_topic_news_task()
            ],
            process=Process.sequential,
            manager_llm=initialize_openai_chat("gpt-4-turbo"),
            verbose=True
        )


def run(topic):
    try:
        one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        inputs = {
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'topic': topic,
            'week_range': f"after:{one_week_ago}",
            'month_range': f"after:{one_month_ago}"
        }
        crew_instance = TopicNewsCrew()
        crew = crew_instance.crew()
        result = crew.kickoff(inputs=inputs)
        logger.info(f"Crew execution result: {result}")
        
        if os.path.exists("analyzed_topic_news.md"):
            with open("analyzed_topic_news.md", "r") as file:
                content = file.read()
            st.markdown(content, unsafe_allow_html=True)
        else:
            st.error("Analyzed topic news file was not created. Check the crew execution result for details.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.error(f"Error in run function: {str(e)}", exc_info=True)

def main():
    st.title("Topic-Specific News Aggregator 🚀")
    
    # Sidebar for API key inputs
    st.sidebar.title("API Key Configuration")
    openai_api_key = get_api_key("OPENAI_API_KEY", "OpenAI API Key")
    serper_api_key = get_api_key("SERPER_API_KEY", "Serper API Key")
    
    # Store API keys in session state
    if openai_api_key:
        st.session_state['OPENAI_API_KEY'] = openai_api_key
        os.environ['OPENAI_API_KEY'] = openai_api_key  # Set the environment variable
        litellm.api_key = openai_api_key  # Set the API key for litellm
    if serper_api_key:
        st.session_state['SERPER_API_KEY'] = serper_api_key
        os.environ['SERPER_API_KEY'] = serper_api_key  # Set the environment variable
    
    # Main app interface
    topic = st.text_input("Enter a topic for news search:")
    if st.button("Generate Topic News"):
        if not topic:
            st.warning("Please enter a topic first.")
        elif not (st.session_state.get('OPENAI_API_KEY') and st.session_state.get('SERPER_API_KEY')):
            st.warning("Please enter both API keys in the sidebar.")
        else:
            try:
                with st.spinner(f"🤖 AI agents working on finding news about {topic}..."):
                    run(topic)
                st.success("✅ Process completed!")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logger.error(f"Error in run function: {str(e)}", exc_info=True)
    
    if st.checkbox("Show logs"):
        log_file = "app.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as file:
                logs = file.read()
            st.text_area("Logs", logs, height=300)
        else:
            st.info("No log file found.")

if __name__ == "__main__":
    main()
