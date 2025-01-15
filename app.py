import autogen 
from typing import Dict 
import json

from config import get_config 

# Configure the agents 
llm_config = get_config() 

class NovelWriter:
    def __init__(self, max_revisions=2):
        # Initialize the agents
        self.editor = autogen.AssistantAgent("editor",
            system_message="""You are a skilled book editor who:
            1. Reviews story premises and provides constructive feedback
            2. Ensures plot consistency and character development
            3. Maintains the overall narrative structure
            4. Provides detailed chapter outlines Please be constructive and specific in your feedback.""",
            llm_config=llm_config )
        
        self.writer = autogen.AssistantAgent("writer",
            system_message="""You are a creative writer who:
            1. Transforms outlines into engaging prose
            2. Creates vivid descriptions and natural dialogue
            3. Maintains consistent character voices
            4. Follows the established plot structure while adding creative details Write in a clear, engaging style without excessive description.
            5. Incorporates feedback to improve chapters""",
            llm_config=llm_config )
        
        self.reviewer = autogen.AssistantAgent("reviewer",
            system_message="""You are a literary critic who:
            1. Reviews completed chapters for quality and consistency
            2. Suggests improvements for pacing and style
            3. Identifies potential plot holes or character inconsistencies
            4. Ensures each chapter advances the story meaningfully Provide specific, actionable feedback.""",
            llm_config=llm_config )
        
        self.user_proxy = autogen.UserProxyAgent(name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "novel_output"}, )
        
        self.max_revisions = max_revisions
        
    def generate_chapter_outline(self, premise: str, chapter_num: int) -> str:
        """Generate an outline for a specific chapter based on the premise."""
        
        chat_manager = autogen.GroupChat( agents=[self.user_proxy, self.editor], messages=[], max_round=5, speaker_selection_method="round_robin")
        
        manager = autogen.GroupChatManager(groupchat=chat_manager)
        
        prompt = f"""Based on the following premise: {premise}
Create a detailed outline for Chapter {chapter_num}
Include:
1. Key plot points
2. Character developments
3. Setting descriptions
4. Major events or revelations
Respond in a structured format suitable for the writer to develop into prose.
"""
        
        self.user_proxy.initiate_chat( manager, message=prompt)
        # Extract the last message from the editor as the outline
        return chat_manager.messages[1]["content"]
        
    def write_chapter(self, outline: str, chapter_num: int, previous_feedback: str = None) -> str:
        """Transform a chapter outline into prose."""

        chat_manager = autogen.GroupChat( agents=[self.user_proxy, self.writer], messages=[], max_round=5, speaker_selection_method="round_robin")
        manager = autogen.GroupChatManager(groupchat=chat_manager)

        feedback_prompt = ""
        if previous_feedback:
            feedback_prompt = f"\nPlease address this feedback in your revision:\n{previous_feedback}"

        prompt = f"""Using this outline for Chapter {chapter_num}:
        
{outline}
{feedback_prompt}

Write the complete chapter in engaging prose. 
Focus on:
1. Natural dialogue and character interactions
2. Vivid but concise descriptions
3. Smooth scene transitions
4. Maintaining consistent pacing Write the chapter now
5. Each chapter MUST contain at least 3000 words
6. Each chapter MUST be self-contained and complete, while advancing the overall story
Write the chapter now, ending with the word TERMINATE
"""
                        
        self.user_proxy.initiate_chat( manager, message=prompt )
        # Extract the last message from the writer as the chapter
        return chat_manager.messages[1]["content"]
    
    def review_chapter(self, chapter: str, chapter_num: int, revision_num: int) -> str: 
        """Review a written chapter and provide feedback."""
        chat_manager = autogen.GroupChat(
            agents=[self.user_proxy, self.reviewer],
            messages=[],
            max_round=3,
            speaker_selection_method="round_robin"
        )
        
        manager = autogen.GroupChatManager(groupchat=chat_manager)
        
        prompt = f"""Review this draft (revision {revision_num}) of Chapter {chapter_num}:
        {chapter}
        
        Provide specific feedback on:
        1. Plot progression and pacing
        2. Character development
        3. Writing style and dialogue
        4. Areas for improvement
        
        If this is revision {revision_num}, be extra thorough in your assessment.
        End your review with TERMINATE"""
        
        self.user_proxy.initiate_chat(
            manager,
            message=prompt
        )
        return chat_manager.messages[1]["content"]
    
    def write_chapter_with_revisions(self, outline: str, chapter_num: int) -> Dict[str, str]:
        """Write a chapter with multiple revisions based on feedback."""
        chapter_versions = {}
        current_feedback = None
        
        for revision in range(self.max_revisions):
            print(f"\nWorking on Chapter {chapter_num}, Revision {revision + 1}...")
            
            # Write chapter (incorporating previous feedback if it exists)
            chapter = self.write_chapter(outline, chapter_num, current_feedback)
            
            # Get feedback on the chapter
            current_feedback = self.review_chapter(chapter, chapter_num, revision + 1)
            
            # Store this version
            chapter_versions[f"revision_{revision + 1}"] = {
                "content": chapter,
                "feedback": current_feedback
            }
            
            # Check if the feedback indicates major issues
            if "excellent" in current_feedback.lower() or "outstanding" in current_feedback.lower():
                print(f"Chapter {chapter_num} achieved satisfactory quality after {revision + 1} revisions.")
                break
        
        return chapter_versions
    
    def write_novel(self, premise: str, num_chapters: int) -> Dict[str, str]:
        """Generate a complete novel based on the premise and number of chapters.""" 
        novel = {} 
        for chapter_num in range(1, num_chapters + 1): 
            print(f"\nWorking on Chapter {chapter_num}...") 
            # Generate chapter outline 
            outline = self.generate_chapter_outline(premise, chapter_num)
            # Write chapter with revisions
            chapter_versions = self.write_chapter_with_revisions(outline, chapter_num)
            # Store chapter and its metadata 
            # Store chapter and its metadata
            novel[f"Chapter_{chapter_num}"] = {
                "outline": outline,
                "versions": chapter_versions,
                # Use the last revision as the final version
                "final_version": chapter_versions[f"revision_{len(chapter_versions)}"]["content"]
            }
            # Save progress after each chapter
            with open(f"novel_output/novel_progress.json", "w") as f:
                json.dump(novel, f, indent=2, separators=(',', ': '))
                f.flush()
        return novel 
            
def main(): 
    # Create the novel_output directory if it doesn't exist 
    import os 
    os.makedirs("novel_output", exist_ok=True) 
    # Example usage 
    novel_writer = NovelWriter(max_revisions=3) 
    premise = open("ideas/foursome.md", "r", encoding="UTF-8").read()
    num_chapters = 2
    novel = novel_writer.write_novel(premise, num_chapters)
    # Save the complete novel
    with open("novel_output/final_novel.json", "w") as f:
        json.dump(novel, f, indent=4)
        # Create a readable text version 
        with open("novel_output/final_novel.txt", "w") as f:
            for chapter_num in range(1, num_chapters + 1):
                chapter_key = f"Chapter_{chapter_num}"
                if "Chapter" not in novel[chapter_key]["final_version"]:
                    f.write(f"\nChapter {chapter_num}\n")
                f.write("=" * 50 + "\n\n")
                f.write(novel[chapter_key]["final_version"])
                f.write("\n\n")
                
if __name__ == "__main__":
    main()
