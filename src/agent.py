import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

try:
    from .tools import (
        create_project_report,
        create_weekly_plan,
        generate_excel_from_request,
        generate_file_from_request,
        generate_image_from_request,
        is_excel_generation_request,
        is_file_generation_request,
        is_image_generation_request,
        search_knowledge_tool,
        summarize_tasks,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from tools import (
        create_project_report,
        create_weekly_plan,
        generate_excel_from_request,
        generate_file_from_request,
        generate_image_from_request,
        is_excel_generation_request,
        is_file_generation_request,
        is_image_generation_request,
        search_knowledge_tool,
        summarize_tasks,
    )


def simple_agent(user_request: str, conversation_history=None):
    req = user_request.lower()

    if is_image_generation_request(user_request):
        return generate_image_from_request(user_request, conversation_history)

    if is_excel_generation_request(user_request):
        return generate_excel_from_request(user_request, conversation_history)

    if is_file_generation_request(user_request):
        return generate_file_from_request(user_request, conversation_history)

    if any(k in req for k in ["weekly", "week", "plan", "kế hoạch", "7 ngày"]):
        return create_weekly_plan(conversation_history)

    if any(k in req for k in ["task", "todo", "việc cần làm", "công việc"]):
        return summarize_tasks()

    if any(k in req for k in ["report", "báo cáo", "project summary", "tóm tắt project"]):
        return create_project_report(conversation_history)

    return search_knowledge_tool(user_request, conversation_history)


if __name__ == "__main__":
    print("Simple Home Agent is ready. Type 'exit' to quit.")
    while True:
        request = input("\nRequest: ").strip()
        if request.lower() in {"exit", "quit"}:
            break
        print("\nResult:\n")
        print(simple_agent(request))
