import autogen 
from typing import Dict 
import json

from config import get_config 

# Configure the agents 
llm_config = get_config() 

class NovelWriter:
    def __init__(self):
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
            4. Follows the established plot structure while adding creative details Write in a clear, engaging style without excessive description.""",
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
4. Major events or revelations Respond in a structured format suitable for the writer to develop into prose.
"""
        
        self.user_proxy.initiate_chat( manager, message=prompt)
        # Extract the last message from the editor as the outline
        return chat_manager.messages[1]["content"]
        
    def write_chapter(self, outline: str, chapter_num: int) -> str:
        """Transform a chapter outline into prose."""
        chat_manager = autogen.GroupChat( agents=[self.user_proxy, self.writer], messages=[], max_round=5, speaker_selection_method="round_robin")
        manager = autogen.GroupChatManager(groupchat=chat_manager)
        prompt = f"""Using this outline for Chapter {chapter_num}: {outline}
Write the complete chapter in engaging prose. 
Focus on:
1. Natural dialogue and character interactions
2. Vivid but concise descriptions
3. Smooth scene transitions
4. Maintaining consistent pacing Write the chapter now
5. Each chapter MUST contain at least 3000 words
6. Each chapter MUST be self-contained and complete, while advancing the overall story
7. End your chapter writing with the word TERMINATE
"""
                        
        self.user_proxy.initiate_chat( manager, message=prompt )
        # Extract the last message from the writer as the chapter
        return chat_manager.messages[1]["content"]
    
    def review_chapter(self, chapter: str, chapter_num: int) -> str: 
        """Review a written chapter and provide feedback."""
        chat_manager = autogen.GroupChat( agents=[self.user_proxy, self.reviewer], messages=[], max_round=3, speaker_selection_method="round_robin")
        manager = autogen.GroupChatManager(groupchat=chat_manager)
        prompt = f"""Review this draft of Chapter {chapter_num}: {chapter}
Provide specific feedback on:
1. Plot progression and pacing
2. Character development
3. Writing style and dialogue
4. Areas for improvement
5. End your review with the word TERMINATE
"""
                        
        self.user_proxy.initiate_chat( manager, message=prompt)
        # Extract the last message from the reviewer as the feedback
        return chat_manager.messages[1]["content"]
    
    def write_novel(self, premise: str, num_chapters: int) -> Dict[str, str]:
        """Generate a complete novel based on the premise and number of chapters.""" 
        novel = {} 
        for chapter_num in range(1, num_chapters + 1): 
            print(f"\nWorking on Chapter {chapter_num}...") 
            # Generate chapter outline 
            outline = self.generate_chapter_outline(premise, chapter_num)
            print(f"Chapter {chapter_num} Outline: {outline}")
            # Write chapter 
            chapter = self.write_chapter(outline, chapter_num)
            # Review chapter 
            feedback = self.review_chapter(chapter, chapter_num)
            # Store chapter and its metadata 
            novel[f"Chapter_{chapter_num}"] = { "outline": outline, "content": chapter, "feedback": feedback }
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
    novel_writer = NovelWriter() 
    premise = open("ideas/unit985.md", "r", encoding="UTF-8").read()
    num_chapters = 25
    novel = novel_writer.write_novel(premise, num_chapters)
    # Save the complete novel
    with open("novel_output/final_novel.json", "w") as f:
        json.dump(novel, f, indent=4)
        # Create a readable text version 
        with open("novel_output/final_novel.txt", "w") as f:
            for chapter_num in range(1, num_chapters + 1):
                chapter_key = f"Chapter_{chapter_num}"
                f.write(f"\nChapter {chapter_num}\n")
                f.write("=" * 50 + "\n\n")
                f.write(novel[chapter_key]["content"])
                f.write("\n\n")
                
if __name__ == "__main__":
    main()
