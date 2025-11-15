import streamlit as st
from src.agents.news_agent import NewsAgent

st.title("Narrative Comparison Agent")

topic = st.text_input("Enter a topic to compare narratives:")

if topic:
    agent = NewsAgent()
    with st.spinner("Analyzing narratives..."):
        comparisons = agent.compare_narratives(topic)

        if comparisons:
            for i, comparison in enumerate(comparisons):
                st.header(f"Cluster {i+1}")
                st.subheader("State-Aligned Summary")
                st.write(comparison.state_aligned_summary)
                st.subheader("Independent Summary")
                st.write(comparison.independent_summary)
                st.subheader("Bias Score")
                st.write(comparison.bias_score)
                st.markdown("---")
        else:
            st.write("No narrative clusters found for this topic.")
