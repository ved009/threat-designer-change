"""
Threat Modeling Prompt Generation Module

This module provides a collection of functions for generating prompts used in security threat modeling analysis.
Each function generates specialized prompts for different phases of the threat modeling process, including:
- Asset identification
- Data flow analysis
- Gap analysis
- Threat identification and improvement
- Response structuring
"""

def summary_prompt() -> str:
    return """<instruction>
Use the information provided by the user to generate a short headline summary of max 40 words.
</instruction> \n
    """


def asset_prompt() -> str:
    return """<instruction>
You are an expert in Security, AWS, and Threat Modeling. Your role is to carefully review a given architecture and identify key assets and entities that require protection. Follow these steps:

1. Review the provided <description> and <assumptions> to understand the solution and security context.

2. Identify the most critical assets within the system, such as sensitive data, databases, communication channels, or APIs. These are components that need protection.

3. Identify the key entities involved, such as users, services, or systems interacting with the system.

4. For each identified asset or entity, provide the following information in the specified format:

Type: [Asset or Entity]
Name: [Asset/Entity Name]
Description: [Brief description of the asset/entity]
</instruction> \n
    """


def flow_prompt(assets_state) -> str:
    return f"""<task>
Analyze the given system architecture and provide the following information:

1. Data Flow Definitions:
- Describe the flow of data through the system, including the source and target entities, and the assets involved.
- Use the following format for each data flow:
<data_flow_definition>
flow_description: [Description of the data flow]
source_entity: [Source entity name]
target_entity: [Target entity name]
assets: [List of assets involved]
</data_flow_definition>

2. Trust Boundaries:
- Identify the trust boundaries where data crosses between different trust zones.
- Use the following format for each trust boundary:
<trust_boundary>
purpose: [Purpose of the trust boundary]
source_entity: [Source entity name]
target_entity: [Target entity name]
</trust_boundary>

3. Threat Actors:
- Identify the relevant threat actors, which are individuals, groups, or entities that have the intent, capability, and opportunity to harm the system's security.
- Use the following format for each threat actor category:
<threat_actor>
category: [Threat actor category]
description: [Description of the threat actor category]
examples: [Examples of the threat actor]
</threat_actor>

Consider the following information provided:
<description> [Description of the solution provided by the user]
<assumptions> [Assumptions provided by the user]

<identified_assets_and_entities>
{assets_state}
</identified_assets_and_entities>
    """


def gap_prompt(gap, assets, system_architecture) -> str:
    return f"""<task_description>
You are an expert in Security, AWS, and Threat Modeling, tasked with validating the comprehensiveness of a provided threat catalog for a given architecture. Your role is to assess the threat model and ensure it covers all relevant aspects, including:
</task_description>

<assessment_criteria>
1. Comprehensive coverage of both technology-specific threats and fundamental security principles applicable universally.
2. Proper mapping of threats to identified threat actors using an attacker-centric approach.
3. Balance between concrete technical mitigations and broader security concepts that remain relevant regardless of the technology stack.
4. Completeness across all potential attack vectors, not just those specific to certain technologies or components.
</assessment_criteria>

<instructions>
1. Carefully review the provided information:
   - <identified_assets_and_entities>{assets}</identified_assets_and_entities>
   - <data_flow>{system_architecture}</data_flow>
   - <threats>Threat Catalog</threats>

2. If a <solution_description> is provided, consider the described solution and the <assumptions> established, as they define the security context and boundaries for analysis.

3. If a previous <gap> analysis is available, take it into account when assessing the <threats> catalog.

<previous_gap>
{gap}
</previous_gap>

4. Think critically and analyze the architecture, identified assets and entities, data flow, and threats.

5. Evaluate whether the <threats> catalog meets the assessment criteria outlined above.

6. Provide your analysis and recommendations for improving the threat catalog's comprehensiveness, if necessary.
</instructions>
    """


def threats_improve_prompt(gap, threat_list, assets, flows) -> str:
    return f"""<task>
You are an expert in Security, AWS, and Threat Modeling. Your role is to enrich an existing threat catalog by identifying new threats that may have been missed, as part of a team working on threat modeling for a given architecture.
</task>

<instructions>
1. Review the provided information:
- <gap>{gap}</gap>: Leverage any gap analysis information to improve the threat catalog.
- <threats>{threat_list}</threats>: The existing threat catalog.
- <identified_assets_and_entities>{assets}</identified_assets_and_entities>: Identified assets and entities in the architecture.
- <data_flow>{flows}</data_flow>: Data flow information.
- <solution_description>: Description of the solution (if provided).
- <assumptions>: Assumptions about the security context and boundaries (if provided).

2. Analyze the architecture, identified assets and entities, data flow, and existing threats carefully.

3. Identify any new relevant threats that may have been missed in the existing threat catalog.

4. When describing new threats, follow these guidelines:
- Ensure the threat description is exhaustive, with 35-50 words.
- Use the provided <threat_grammar> structure:
<threat_grammar>
[threat actor category] [prerequisites] can [threat action] which leads to [threat impact], negatively impacting [impacted assets].
</threat_grammar>

5. Consider the STRIDE model for each identified asset and entity:
- S (Spoofing): How could an attacker impersonate legitimate users, services, or system components?
- T (Tampering): How could data or components be modified in unauthorized ways, both in transit and at rest?
- R (Repudiation): Could any actions be performed without proper logging, enabling users to deny them?
- I (Information Disclosure): How might sensitive data be exposed to unauthorized entities?
- D (Denial of Service): How could an attacker disrupt services, making them unavailable to legitimate users?
- E (Elevation of Privilege): How might attackers gain unauthorized access to higher privilege levels or roles?

6. Provide new threats in the specified <output_format>, including threat name, STRIDE category, description, target, impact, likelihood, and mitigations.
<output_format>
Threat Name: [Threat Name]
STRIDE Category: [Select one: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege]
Description: [description of the threat]
Target: [What asset or component is being targeted]
Impact: [Potential consequences if the threat is realized]
Likelihood: [Estimated probability of occurrence: Low/Medium/High]
Mitigations:
1. [Mitigation strategy 1]
....
N. [Mitigation strategy N]
</output_format>

7. When creating threat models, ensure comprehensive coverage by:
- Thinking like an attacker and identifying both technology-specific threats and fundamental security principles that apply universally.
- Providing an exhaustive list of threats mapped to identified threat actors and data flows.
- Balancing concrete technical mitigations with broader security concepts that remain relevant regardless of the underlying technology stack or application type.
</instructions>
        """


def threats_prompt(assets, flows) -> str:
    return f"""<task>
You are an expert in Security, AWS, and Threat Modeling. Your task is to generate a comprehensive list of threats for a given architecture by analyzing the provided information and following the specified output format. You are part of a team of assistants whose overall goal is to perform threat modeling on a given architecture. Your specific role is to leverage the information provided by your peers in the following sections
</task>


<instructions>
1. Review the provided information:
- <identified_assets_and_entities>{assets}</identified_assets_and_entities>: Identified assets and entities in the architecture.
- <data_flow>{flows}</data_flow>: Data flow information.
- <solution_description>: Description of the solution (if provided).
- <assumptions>: Assumptions about the security context and boundaries (if provided).

2. Analyze the architecture, identified assets and entities, data flow, carefully.

3. When describing new threats, follow these guidelines:
- Ensure the threat description is exhaustive, with 35-50 words.
- Use the provided <threat_grammar> structure:
<threat_grammar>
[threat actor category] [prerequisites] can [threat action] which leads to [threat impact], negatively impacting [impacted assets].
</threat_grammar>

4. Consider the STRIDE model for each identified asset and entity:
- S (Spoofing): How could an attacker impersonate legitimate users, services, or system components?
- T (Tampering): How could data or components be modified in unauthorized ways, both in transit and at rest?
- R (Repudiation): Could any actions be performed without proper logging, enabling users to deny them?
- I (Information Disclosure): How might sensitive data be exposed to unauthorized entities?
- D (Denial of Service): How could an attacker disrupt services, making them unavailable to legitimate users?
- E (Elevation of Privilege): How might attackers gain unauthorized access to higher privilege levels or roles?

5. Provide new threats in the specified <output_format>, including threat name, STRIDE category, description, target, impact, likelihood, and mitigations.
<output_format>
Threat Name: [Threat Name]
STRIDE Category: [Select one: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege]
Description: [description of the threat]
Target: [What asset or component is being targeted]
Impact: [Potential consequences if the threat is realized]
Likelihood: [Estimated probability of occurrence: Low/Medium/High]
Mitigations:
1. [Mitigation strategy 1]
....
N. [Mitigation strategy N]
</output_format>

6. When creating threat models, ensure comprehensive coverage by:
- Thinking like an attacker and identifying both technology-specific threats and fundamental security principles that apply universally.
- Providing an exhaustive list of threats mapped to identified threat actors and data flows.
- Balancing concrete technical mitigations with broader security concepts that remain relevant regardless of the underlying technology stack or application type.
</instructions>
"""





def structure_prompt(data) -> str:
    return f"""You are an helpful assistant whose goal is to to convert the response from your colleague
     to the desired structured output. The response is provided within <response> \n
     <response>
     {data}
     </response>
     """
