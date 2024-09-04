import json
from rich.console import Console

from mle.function import *
from mle.integration import GitHubIntegration


class SummaryAgent:

    def __init__(self, model, github_repo: str, github_token: str = None, console=None):
        """
        SummaryAgent: summary the workspace provided by the user.

        Args:
            model: the model to use.
            github_token: the Github token to use, if None, will fetch from the environment variable.
            github_repo: the Github repo to summarize.
            console: the console to use.
        """
        self.report = None
        self.model = model
        self.chat_history = []
        self.github_repo = github_repo
        self.github = GitHubIntegration(github_repo, github_token)
        self.console = console
        if not self.console:
            self.console = Console()
        self.sys_prompt = """
        You are a software expert tasked with summarizing the Github project information provided by the user. The
         project may contain the dataset, the source code, and the documentation, etc.

        Your capabilities include:

        1. You need to summarize the basic project information, including the project name, the project description,
            the technical stacks, etc.
        2. You need to further analyze the project structure and the README file to understand the project business goal
         and the purpose. And give a deep understanding of the project, draw a summary in the description.
        3. You need to analyze the issue list, summarize and infer the project roadmap and TODO-list.
        4. You should read the README.md file and see if the project includes a dataset (or using a public dataset).
         if so, you'd better give a brief introduction to the dataset.
        5. Based on the information provided, you need to guess the technical hard parts and give suggestions.
        6. You may use function `search_arxiv` and `search_github_repos` to search for the related papers and github
         repos of the project using the project keywords and tech stacks. Do not directly search the project name.

        """
        self.json_mode_prompt = """

        JSON Output Format:

        {
            "summary": "The project is a ...",
            "business_goal": ["The project aims to build an image classification model...", ...],
            "dataset": [{"name": "CIFAR-10", "description": "The project uses CIFAR-10 dataset to train
             the classification model. The dataset includes 10 classes of images...""}, ...],
            "tech_stack": ["Python", "PyTorch", "MLFlow", ...],
            "roadmap": [{"task": "fix ...", "priority": "high"}, {"task": "support ...", "priority": "medium"}, ...],
            "hard_parts": ["The project may face the challenge of ...", ...],
            "related_work": ["https://arxiv.org/abs/1409.0575", "https://github.com/MLSysOps/MLE-Agent", ...],
        }

        """
        self.functions = [
            schema_search_arxiv,
            schema_search_github_repos,
            schema_search_papers_with_code
        ]

        self.sys_prompt += self.json_mode_prompt
        self.chat_history.append({"role": 'system', "content": self.sys_prompt})

    def process_knowledge(self):
        """
        Process the knowledge from the Github repo.
        Args: None
        """
        info_str = f"""
        GITHUB REPO: {self.github_repo}
        """
        readme_content = self.github.get_readme()
        issues = self.github.get_issues(open_only=True)
        repo_files = self.github.get_structure(include_invisible=False)

        info_str += f"""

        README CONTENT:
        {readme_content}

        ISSUE LIST:
        """

        for issue in issues:
            info_str += f"""

            Title: {issue['title']}
            Author: {issue['author']}
            State: {issue['state']}
            Created At: {issue['created_at']}
            """

        info_str += f"""

        PROJECT STRUCTURE:
        """

        for file in repo_files:
            info_str += f"""
            {file}
            """

        return info_str

    def summarize(self):
        """
        Handle the query from the model query response.
        Args: None
        """
        with self.console.status("MLE summarizer is summarizing the project..."):
            self.chat_history.append({"role": "user", "content": self.process_knowledge()})
            text = self.model.query(
                self.chat_history,
                function_call='auto',
                functions=self.functions,
                response_format={"type": "json_object"}
            )

            self.chat_history.append({"role": "assistant", "content": text})
            summary = json.loads(text)

        return summary
