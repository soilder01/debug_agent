from pydantic import BaseModel

from debug_agent.orchestration.taxonomy import logical_agent_roles as taxonomy_agent_roles


class AgentRole(BaseModel):
    role_id: str
    display_name: str
    responsibility: str


def logical_agent_roles() -> list[AgentRole]:
    return [
        AgentRole(
            role_id=role.role_id,
            display_name=role.display_name,
            responsibility=role.responsibility,
        )
        for role in taxonomy_agent_roles()
    ]
