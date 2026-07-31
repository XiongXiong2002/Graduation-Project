# third-party dependencies
from sqlalchemy import Column, Integer, String, Text

# database
from database import Base


class AIReference(Base):
    __tablename__ = "ai_references"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    title = Column(String, nullable=False)
    writer = Column(String(100), nullable=False)
    source = Column(String(500), nullable=False)
    # Allowed categories: academic, stress, interpersonal, economic, other.
    problem_type = Column(String(100), nullable=False)
