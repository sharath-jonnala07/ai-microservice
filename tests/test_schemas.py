from app.models.schemas import ChatRequest


def test_question_is_normalized() -> None:
    payload = ChatRequest(question="  What   is the   exit load?  ")
    assert payload.question == "What is the exit load?"