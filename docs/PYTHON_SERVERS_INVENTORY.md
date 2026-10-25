# echelon — tool inventory (82 tools)


### activate_workflow
- impl: `tools/workflow_tools.py:592` | params_model: `ActivateWorkflowParams`
- desc: Activate a workflow in ServiceNow
- params: workflow_id:str
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}`
- methods: PATCH

### add_change_task
- impl: `tools/change_tools.py:584` | params_model: `AddChangeTaskParams`
- desc: Add a task to a change request
- params: change_id:str, short_description:str, description:Optional[str]=None, assigned_to:Optional[str]=None, planned_start_date:Optional[str]=None, planned_end_date:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_task`
- methods: POST

### add_comment
- impl: `tools/incident_tools.py:277` | params_model: `AddCommentParams`
- desc: Add a comment to an incident in ServiceNow
- params: incident_id:str, comment:str, is_work_note:bool=None
- endpoint: `{api_url}/table/incident`
- endpoint: `{api_url}/table/incident/{incident_id}`
- methods: GET, PUT

### add_file_to_changeset
- impl: `tools/changeset_tools.py:694` | params_model: `AddFileToChangesetParams`
- desc: Add a file to a changeset in ServiceNow
- params: changeset_id:str, file_path:str, file_content:str
- endpoint: `{instance_url}/api/now/table/sys_update_xml`
- methods: POST

### add_group_members
- impl: `tools/user_tools.py:747` | params_model: `AddGroupMembersParams`
- desc: Add members to an existing group in ServiceNow
- params: group_id:str, members:List[str]
- endpoint: `{api_url}/table/sys_user_grmember`
- methods: POST

### add_workflow_activity
- impl: `tools/workflow_tools.py:704` | params_model: `AddWorkflowActivityParams`
- desc: Add a new activity to a workflow in ServiceNow
- params: workflow_version_id:str, name:str, description:Optional[str]=None, activity_type:str, attributes:Optional[Dict[str, Any]]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_activity`
- methods: POST

### approve_change
- impl: `tools/change_tools.py:758` | params_model: `ApproveChangeParams`
- desc: Approve a change request
- params: change_id:str, approver_id:Optional[str]=None, approval_comments:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_request/{validated_params.change_id}`
- endpoint: `{instance_url}/api/now/table/sysapproval_approver`
- endpoint: `{instance_url}/api/now/table/sysapproval_approver/{approval_id}`
- methods: GET, PATCH

### commit_changeset
- impl: `tools/changeset_tools.py:538` | params_model: `CommitChangesetParams`
- desc: Commit a changeset in ServiceNow
- params: changeset_id:str, commit_message:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}`
- methods: PATCH

### create_article
- impl: `tools/knowledge_base.py:397` | params_model: `CreateArticleParams`
- desc: Create a new knowledge article
- params: title:str, text:str, short_description:str, knowledge_base:str, category:str, keywords:Optional[str]=None, article_type:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge`
- methods: POST

### create_catalog_category
- impl: `tools/catalog_tools.py:393` | params_model: `CreateCatalogCategoryParams`
- desc: Create a new service catalog category.
- params: title:str, description:Optional[str]=None, parent:Optional[str]=None, icon:Optional[str]=None, active:bool=None, order:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/sc_category`
- methods: POST

### create_catalog_item_variable
- impl: `tools/catalog_variables.py:81` | params_model: `CreateCatalogItemVariableParams`
- desc: Create a new catalog item variable
- params: catalog_item_id:str, name:str, type:str, label:str, mandatory:bool=None, help_text:Optional[str]=None, default_value:Optional[str]=None, description:Optional[str]=None, order:Optional[int]=None, reference_table:Optional[str]=None, reference_qualifier:Optional[str]=None, max_length:Optional[int]=None, min:Optional[int]=None, max:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/item_option_new`
- methods: POST

### create_category
- impl: `?:?` | params_model: `CreateKBCategoryParams`
- desc: Create a new category in a knowledge base
- params: title:str, description:Optional[str]=None, knowledge_base:str, parent_category:Optional[str]=None, parent_table:Optional[str]=None, active:bool=None

### create_change_request
- impl: `tools/change_tools.py:209` | params_model: `CreateChangeRequestParams`
- desc: Create a new change request in ServiceNow
- params: short_description:str, description:Optional[str]=None, type:str, risk:Optional[str]=None, impact:Optional[str]=None, category:Optional[str]=None, requested_by:Optional[str]=None, assignment_group:Optional[str]=None, start_date:Optional[str]=None, end_date:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_request`
- methods: POST

### create_changeset
- impl: `tools/changeset_tools.py:368` | params_model: `CreateChangesetParams`
- desc: Create a new changeset in ServiceNow
- params: name:str, description:Optional[str]=None, application:str, developer:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/sys_update_set`
- methods: POST

### create_epic
- impl: `tools/epic_tools.py:157` | params_model: `CreateEpicParams`
- desc: Create a new epic in ServiceNow
- params: short_description:str, description:Optional[str]=None, priority:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_epic`
- methods: POST

### create_group
- impl: `tools/user_tools.py:614` | params_model: `CreateGroupParams`
- desc: Create a new group in ServiceNow
- params: name:str, description:Optional[str]=None, manager:Optional[str]=None, parent:Optional[str]=None, type:Optional[str]=None, email:Optional[str]=None, members:Optional[List[str]]=None, active:Optional[bool]=None
- endpoint: `{api_url}/table/sys_user_group`
- methods: POST

### create_incident
- impl: `tools/incident_tools.py:95` | params_model: `CreateIncidentParams`
- desc: Create a new incident in ServiceNow
- params: short_description:str, description:Optional[str]=None, caller_id:Optional[str]=None, category:Optional[str]=None, subcategory:Optional[str]=None, priority:Optional[str]=None, impact:Optional[str]=None, urgency:Optional[str]=None, assigned_to:Optional[str]=None, assignment_group:Optional[str]=None
- endpoint: `{api_url}/table/incident`
- methods: POST

### create_knowledge_base
- impl: `tools/knowledge_base.py:137` | params_model: `CreateKnowledgeBaseParams`
- desc: Create a new knowledge base in ServiceNow
- params: title:str, description:Optional[str]=None, owner:Optional[str]=None, managers:Optional[str]=None, publish_workflow:Optional[str]=None, retire_workflow:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge_base`
- methods: POST

### create_project
- impl: `tools/project_tools.py:163` | params_model: `CreateProjectParams`
- desc: Create a new project in ServiceNow
- params: short_description:str, description:Optional[str]=None, status:Optional[str]=None, state:Optional[str]=None, project_manager:Optional[str]=None, percentage_complete:Optional[int]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, start_date:Optional[str]=None, end_date:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/pm_project`
- methods: POST

### create_script_include
- impl: `tools/script_include_tools.py:262` | params_model: `CreateScriptIncludeParams`
- desc: Create a new script include in ServiceNow
- params: name:str, script:str, description:Optional[str]=None, api_name:Optional[str]=None, client_callable:bool=None, active:bool=None, access:str=None
- endpoint: `{config.instance_url}/api/now/table/sys_script_include`
- methods: POST

### create_scrum_task
- impl: `tools/scrum_task_tools.py:166` | params_model: `CreateScrumTaskParams`
- desc: Create a new scrum task in ServiceNow
- params: story:str, short_description:str, priority:Optional[str]=None, planned_hours:Optional[int]=None, remaining_hours:Optional[int]=None, hours:Optional[int]=None, description:Optional[str]=None, type:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_scrum_task`
- methods: POST

### create_story
- impl: `tools/story_tools.py:182` | params_model: `CreateStoryParams`
- desc: Create a new story in ServiceNow
- params: short_description:str, acceptance_criteria:str, description:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, story_points:Optional[int]=None, assigned_to:Optional[str]=None, epic:Optional[str]=None, project:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_story`
- methods: POST

### create_story_dependency
- impl: `tools/story_tools.py:560` | params_model: `CreateStoryDependencyParams`
- desc: Create a dependency between two stories in ServiceNow
- params: dependent_story:str, prerequisite_story:str
- endpoint: `{instance_url}/api/now/table/m2m_story_dependencies`
- methods: POST

### create_user
- impl: `tools/user_tools.py:154` | params_model: `CreateUserParams`
- desc: Create a new user in ServiceNow
- params: user_name:str, first_name:str, last_name:str, email:str, title:Optional[str]=None, department:Optional[str]=None, manager:Optional[str]=None, roles:Optional[List[str]]=None, phone:Optional[str]=None, mobile_phone:Optional[str]=None, location:Optional[str]=None, password:Optional[str]=None, active:Optional[bool]=None
- endpoint: `{api_url}/table/sys_user`
- methods: POST

### create_workflow
- impl: `tools/workflow_tools.py:450` | params_model: `CreateWorkflowParams`
- desc: Create a new workflow in ServiceNow
- params: name:str, description:Optional[str]=None, table:Optional[str]=None, active:Optional[bool]=None, attributes:Optional[Dict[str, Any]]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow`
- methods: POST

### deactivate_workflow
- impl: `tools/workflow_tools.py:648` | params_model: `DeactivateWorkflowParams`
- desc: Deactivate a workflow in ServiceNow
- params: workflow_id:str
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}`
- methods: PATCH

### delete_script_include
- impl: `tools/script_include_tools.py:432` | params_model: `DeleteScriptIncludeParams`
- desc: Delete a script include in ServiceNow
- params: script_include_id:str
- endpoint: `{config.instance_url}/api/now/table/sys_script_include/{sys_id}`
- methods: DELETE

### delete_story_dependency
- impl: `tools/story_tools.py:632` | params_model: `DeleteStoryDependencyParams`
- desc: Delete a story dependency in ServiceNow
- params: dependency_id:str
- endpoint: `{instance_url}/api/now/table/m2m_story_dependencies/{validated_params.dependency_id}`
- methods: DELETE

### delete_workflow_activity
- impl: `tools/workflow_tools.py:843` | params_model: `DeleteWorkflowActivityParams`
- desc: Delete an activity from a workflow
- params: activity_id:str
- endpoint: `{server_config.instance_url}/api/now/table/wf_activity/{activity_id}`
- methods: DELETE

### get_article
- impl: `tools/knowledge_base.py:706` | params_model: `GetArticleParams`
- desc: Get a specific knowledge article by ID
- params: article_id:str
- endpoint: `{api_url}/table/kb_knowledge/{params.article_id}`
- methods: GET

### get_catalog_item
- impl: `tools/catalog_tools.py:170` | params_model: `GetCatalogItemParams`
- desc: Get a specific service catalog item.
- params: item_id:str
- endpoint: `{config.instance_url}/api/now/table/sc_cat_item/{params.item_id}`
- methods: GET

### get_change_request_details
- impl: `tools/change_tools.py:502` | params_model: `GetChangeRequestDetailsParams`
- desc: Get detailed information about a specific change request
- params: change_id:str
- endpoint: `{instance_url}/api/now/table/change_request/{validated_params.change_id}`
- endpoint: `{instance_url}/api/now/table/change_task`
- methods: GET

### get_changeset_details
- impl: `tools/changeset_tools.py:286` | params_model: `GetChangesetDetailsParams`
- desc: Get detailed information about a specific changeset
- params: changeset_id:str
- endpoint: `{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}`
- endpoint: `{instance_url}/api/now/table/sys_update_xml`
- methods: GET

### get_incident_by_number
- impl: `tools/incident_tools.py:548` | params_model: `GetIncidentByNumberParams`
- desc: Incident details from ServiceNow
- params: incident_number:str
- endpoint: `{api_url}/table/incident`
- methods: GET

### get_optimization_recommendations
- impl: `tools/catalog_optimization.py:43` | params_model: `OptimizationRecommendationsParams`
- desc: Get optimization recommendations for the service catalog.
- params: recommendation_types:List[str]=None, category_id:Optional[str]=None

### get_script_include
- impl: `tools/script_include_tools.py:169` | params_model: `GetScriptIncludeParams`
- desc: Get a specific script include from ServiceNow
- params: script_include_id:str
- endpoint: `{config.instance_url}/api/now/table/sys_script_include`
- endpoint: `{config.instance_url}/api/now/table/sys_script_include/{sys_id}`
- methods: GET

### get_user
- impl: `tools/user_tools.py:303` | params_model: `GetUserParams`
- desc: Get a specific user in ServiceNow
- params: user_id:Optional[str]=None, user_name:Optional[str]=None, email:Optional[str]=None
- endpoint: `{api_url}/table/sys_user`
- methods: GET

### get_workflow_activities
- impl: `tools/workflow_tools.py:360` | params_model: `GetWorkflowActivitiesParams`
- desc: Get activities for a specific workflow
- params: workflow_id:str, version:Optional[str]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_activity`
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow_version`
- methods: GET

### get_workflow_details
- impl: `tools/workflow_tools.py:251` | params_model: `GetWorkflowDetailsParams`
- desc: Get detailed information about a specific workflow
- params: workflow_id:str, include_versions:Optional[bool]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}`
- methods: GET

### list_articles
- impl: `tools/knowledge_base.py:571` | params_model: `ListArticlesParams`
- desc: List knowledge articles
- params: limit:int=None, offset:int=None, knowledge_base:Optional[str]=None, category:Optional[str]=None, query:Optional[str]=None, workflow_state:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge`
- methods: GET

### list_catalog_categories
- impl: `tools/catalog_tools.py:308` | params_model: `ListCatalogCategoriesParams`
- desc: List service catalog categories.
- params: limit:int=None, offset:int=None, query:Optional[str]=None, active:bool=None
- endpoint: `{config.instance_url}/api/now/table/sc_category`
- methods: GET

### list_catalog_item_variables
- impl: `tools/catalog_variables.py:154` | params_model: `ListCatalogItemVariablesParams`
- desc: List catalog item variables
- params: catalog_item_id:str, include_details:bool=None, limit:Optional[int]=None, offset:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/item_option_new`
- methods: GET

### list_catalog_items
- impl: `tools/catalog_tools.py:82` | params_model: `ListCatalogItemsParams`
- desc: List service catalog items.
- params: limit:int=None, offset:int=None, category:Optional[str]=None, query:Optional[str]=None, active:bool=None
- endpoint: `{config.instance_url}/api/now/table/sc_cat_item`
- methods: GET

### list_categories
- impl: `?:?` | params_model: `ListKBCategoriesParams`
- desc: List categories in a knowledge base
- params: knowledge_base:Optional[str]=None, parent_category:Optional[str]=None, limit:int=None, offset:int=None, active:Optional[bool]=None, query:Optional[str]=None

### list_change_requests
- impl: `tools/change_tools.py:396` | params_model: `ListChangeRequestsParams`
- desc: List change requests from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, state:Optional[str]=None, type:Optional[str]=None, category:Optional[str]=None, assignment_group:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_request`
- methods: GET

### list_changesets
- impl: `tools/changeset_tools.py:192` | params_model: `ListChangesetsParams`
- desc: List changesets from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, state:Optional[str]=None, application:Optional[str]=None, developer:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/sys_update_set`
- methods: GET

### list_epics
- impl: `tools/epic_tools.py:328` | params_model: `ListEpicsParams`
- desc: List epics from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, priority:Optional[str]=None, assignment_group:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_epic`
- methods: GET

### list_groups
- impl: `tools/user_tools.py:417` | params_model: `ListGroupsParams`
- desc: List groups from ServiceNow with optional filtering
- params: limit:int=None, offset:int=None, active:Optional[bool]=None, query:Optional[str]=None, type:Optional[str]=None
- endpoint: `{api_url}/table/sys_user_group`
- methods: GET

### list_incidents
- impl: `tools/incident_tools.py:459` | params_model: `ListIncidentsParams`
- desc: List incidents from ServiceNow
- params: limit:int=None, offset:int=None, state:Optional[str]=None, assigned_to:Optional[str]=None, category:Optional[str]=None, query:Optional[str]=None
- endpoint: `{api_url}/table/incident`
- methods: GET

### list_knowledge_bases
- impl: `tools/knowledge_base.py:198` | params_model: `ListKnowledgeBasesParams`
- desc: List knowledge bases from ServiceNow
- params: limit:int=None, offset:int=None, active:Optional[bool]=None, query:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge_base`
- methods: GET

### list_projects
- impl: `tools/project_tools.py:350` | params_model: `ListProjectsParams`
- desc: List projects from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/pm_project`
- methods: GET

### list_script_includes
- impl: `tools/script_include_tools.py:74` | params_model: `ListScriptIncludesParams`
- desc: List script includes from ServiceNow
- params: limit:int=None, offset:int=None, active:Optional[bool]=None, client_callable:Optional[bool]=None, query:Optional[str]=None
- endpoint: `{config.instance_url}/api/now/table/sys_script_include`
- methods: GET

### list_scrum_tasks
- impl: `tools/scrum_task_tools.py:358` | params_model: `ListScrumTasksParams`
- desc: List scrum tasks from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_scrum_task`
- methods: GET

### list_stories
- impl: `tools/story_tools.py:368` | params_model: `ListStoriesParams`
- desc: List stories from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, timeframe:Optional[str]=None, query:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_story`
- methods: GET

### list_story_dependencies
- impl: `tools/story_tools.py:469` | params_model: `ListStoryDependenciesParams`
- desc: List story dependencies from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, query:Optional[str]=None, dependent_story:Optional[str]=None, prerequisite_story:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/m2m_story_dependencies`
- methods: GET

### list_users
- impl: `tools/user_tools.py:356` | params_model: `ListUsersParams`
- desc: List users in ServiceNow
- params: limit:int=None, offset:int=None, active:Optional[bool]=None, department:Optional[str]=None, query:Optional[str]=None
- endpoint: `{api_url}/table/sys_user`
- methods: GET

### list_workflow_versions
- impl: `tools/workflow_tools.py:300` | params_model: `ListWorkflowVersionsParams`
- desc: List workflow versions from ServiceNow
- params: workflow_id:str, limit:Optional[int]=None, offset:Optional[int]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow_version`
- methods: GET

### list_workflows
- impl: `tools/workflow_tools.py:183` | params_model: `ListWorkflowsParams`
- desc: List workflows from ServiceNow
- params: limit:Optional[int]=None, offset:Optional[int]=None, active:Optional[bool]=None, name:Optional[str]=None, query:Optional[str]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow`
- methods: GET

### move_catalog_items
- impl: `tools/catalog_tools.py:544` | params_model: `MoveCatalogItemsParams`
- desc: Move catalog items to a different category.
- params: item_ids:List[str], target_category_id:str
- endpoint: `{config.instance_url}/api/now/table/sc_cat_item`
- methods: PATCH

### publish_article
- impl: `tools/knowledge_base.py:517` | params_model: `PublishArticleParams`
- desc: Publish a knowledge article
- params: article_id:str, workflow_state:Optional[str]=None, workflow_version:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge/{params.article_id}`
- methods: PATCH

### publish_changeset
- impl: `tools/changeset_tools.py:616` | params_model: `PublishChangesetParams`
- desc: Publish a changeset in ServiceNow
- params: changeset_id:str, publish_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}`
- methods: PATCH

### reject_change
- impl: `tools/change_tools.py:860` | params_model: `RejectChangeParams`
- desc: Reject a change request
- params: change_id:str, approver_id:Optional[str]=None, rejection_reason:str
- endpoint: `{instance_url}/api/now/table/change_request/{validated_params.change_id}`
- endpoint: `{instance_url}/api/now/table/sysapproval_approver`
- endpoint: `{instance_url}/api/now/table/sysapproval_approver/{approval_id}`
- methods: GET, PATCH

### remove_group_members
- impl: `tools/user_tools.py:814` | params_model: `RemoveGroupMembersParams`
- desc: Remove members from an existing group in ServiceNow
- params: group_id:str, members:List[str]
- endpoint: `{api_url}/table/sys_user_grmember`
- methods: DELETE, GET

### reorder_workflow_activities
- impl: `tools/workflow_tools.py:893` | params_model: `ReorderWorkflowActivitiesParams`
- desc: Reorder activities in a workflow
- params: workflow_id:str, activity_ids:List[str]
- endpoint: `{server_config.instance_url}/api/now/table/wf_activity/{activity_id}`
- methods: PATCH

### resolve_incident
- impl: `tools/incident_tools.py:368` | params_model: `ResolveIncidentParams`
- desc: Resolve an incident in ServiceNow
- params: incident_id:str, resolution_code:str, resolution_notes:str
- endpoint: `{api_url}/table/incident`
- endpoint: `{api_url}/table/incident/{incident_id}`
- methods: GET, PUT

### submit_change_for_approval
- impl: `tools/change_tools.py:669` | params_model: `SubmitChangeForApprovalParams`
- desc: Submit a change request for approval
- params: change_id:str, approval_comments:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_request/{validated_params.change_id}`
- endpoint: `{instance_url}/api/now/table/sysapproval_approver`
- methods: PATCH, POST

### update_article
- impl: `tools/knowledge_base.py:457` | params_model: `UpdateArticleParams`
- desc: Update an existing knowledge article
- params: article_id:str, title:Optional[str]=None, text:Optional[str]=None, short_description:Optional[str]=None, category:Optional[str]=None, keywords:Optional[str]=None
- endpoint: `{api_url}/table/kb_knowledge/{params.article_id}`
- methods: PATCH

### update_catalog_category
- impl: `tools/catalog_tools.py:469` | params_model: `UpdateCatalogCategoryParams`
- desc: Update an existing service catalog category.
- params: category_id:str, title:Optional[str]=None, description:Optional[str]=None, parent:Optional[str]=None, icon:Optional[str]=None, active:Optional[bool]=None, order:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/sc_category/{params.category_id}`
- methods: PATCH

### update_catalog_item
- impl: `tools/catalog_optimization.py:144` | params_model: `UpdateCatalogItemParams`
- desc: Update a service catalog item.
- params: item_id:str=None, name:Optional[str]=None, short_description:Optional[str]=None, description:Optional[str]=None, category:Optional[str]=None, price:Optional[str]=None, active:Optional[bool]=None, order:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/sc_cat_item/{params.item_id}`
- methods: PATCH

### update_catalog_item_variable
- impl: `tools/catalog_variables.py:216` | params_model: `UpdateCatalogItemVariableParams`
- desc: Update a catalog item variable
- params: variable_id:str, label:Optional[str]=None, mandatory:Optional[bool]=None, help_text:Optional[str]=None, default_value:Optional[str]=None, description:Optional[str]=None, order:Optional[int]=None, reference_qualifier:Optional[str]=None, max_length:Optional[int]=None, min:Optional[int]=None, max:Optional[int]=None
- endpoint: `{config.instance_url}/api/now/table/item_option_new/{params.variable_id}`
- methods: PATCH

### update_change_request
- impl: `tools/change_tools.py:302` | params_model: `UpdateChangeRequestParams`
- desc: Update an existing change request in ServiceNow
- params: change_id:str, short_description:Optional[str]=None, description:Optional[str]=None, state:Optional[str]=None, risk:Optional[str]=None, impact:Optional[str]=None, category:Optional[str]=None, assignment_group:Optional[str]=None, start_date:Optional[str]=None, end_date:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/change_request/{validated_params.change_id}`
- methods: PUT

### update_changeset
- impl: `tools/changeset_tools.py:449` | params_model: `UpdateChangesetParams`
- desc: Update an existing changeset in ServiceNow
- params: changeset_id:str, name:Optional[str]=None, description:Optional[str]=None, state:Optional[str]=None, developer:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/sys_update_set/{validated_params.changeset_id}`
- methods: PATCH

### update_epic
- impl: `tools/epic_tools.py:243` | params_model: `UpdateEpicParams`
- desc: Update an existing epic in ServiceNow
- params: epic_id:str, short_description:Optional[str]=None, description:Optional[str]=None, priority:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_epic/{validated_params.epic_id}`
- methods: PUT

### update_group
- impl: `tools/user_tools.py:685` | params_model: `UpdateGroupParams`
- desc: Update an existing group in ServiceNow
- params: group_id:str, name:Optional[str]=None, description:Optional[str]=None, manager:Optional[str]=None, parent:Optional[str]=None, type:Optional[str]=None, email:Optional[str]=None, active:Optional[bool]=None
- endpoint: `{api_url}/table/sys_user_group/{params.group_id}`
- methods: PATCH

### update_incident
- impl: `tools/incident_tools.py:164` | params_model: `UpdateIncidentParams`
- desc: Update an existing incident in ServiceNow
- params: incident_id:str, short_description:Optional[str]=None, description:Optional[str]=None, state:Optional[str]=None, category:Optional[str]=None, subcategory:Optional[str]=None, priority:Optional[str]=None, impact:Optional[str]=None, urgency:Optional[str]=None, assigned_to:Optional[str]=None, assignment_group:Optional[str]=None, work_notes:Optional[str]=None, close_notes:Optional[str]=None, close_code:Optional[str]=None
- endpoint: `{api_url}/table/incident`
- endpoint: `{api_url}/table/incident/{incident_id}`
- methods: GET, PUT

### update_project
- impl: `tools/project_tools.py:257` | params_model: `UpdateProjectParams`
- desc: Update an existing project in ServiceNow
- params: project_id:str, short_description:Optional[str]=None, description:Optional[str]=None, status:Optional[str]=None, state:Optional[str]=None, project_manager:Optional[str]=None, percentage_complete:Optional[int]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, start_date:Optional[str]=None, end_date:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/pm_project/{validated_params.project_id}`
- methods: PUT

### update_script_include
- impl: `tools/script_include_tools.py:333` | params_model: `UpdateScriptIncludeParams`
- desc: Update an existing script include in ServiceNow
- params: script_include_id:str, script:Optional[str]=None, description:Optional[str]=None, api_name:Optional[str]=None, client_callable:Optional[bool]=None, active:Optional[bool]=None, access:Optional[str]=None
- endpoint: `{config.instance_url}/api/now/table/sys_script_include/{sys_id}`
- methods: PATCH

### update_scrum_task
- impl: `tools/scrum_task_tools.py:263` | params_model: `UpdateScrumTaskParams`
- desc: Update an existing scrum task in ServiceNow
- params: scrum_task_id:str, short_description:Optional[str]=None, priority:Optional[str]=None, planned_hours:Optional[int]=None, remaining_hours:Optional[int]=None, hours:Optional[int]=None, description:Optional[str]=None, type:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, assigned_to:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_scrum_task/{validated_params.scrum_task_id}`
- methods: PUT

### update_story
- impl: `tools/story_tools.py:275` | params_model: `UpdateStoryParams`
- desc: Update an existing story in ServiceNow
- params: story_id:str, short_description:Optional[str]=None, acceptance_criteria:Optional[str]=None, description:Optional[str]=None, state:Optional[str]=None, assignment_group:Optional[str]=None, story_points:Optional[int]=None, assigned_to:Optional[str]=None, epic:Optional[str]=None, project:Optional[str]=None, work_notes:Optional[str]=None
- endpoint: `{instance_url}/api/now/table/rm_story/{validated_params.story_id}`
- methods: PUT

### update_user
- impl: `tools/user_tools.py:227` | params_model: `UpdateUserParams`
- desc: Update an existing user in ServiceNow
- params: user_id:str, user_name:Optional[str]=None, first_name:Optional[str]=None, last_name:Optional[str]=None, email:Optional[str]=None, title:Optional[str]=None, department:Optional[str]=None, manager:Optional[str]=None, roles:Optional[List[str]]=None, phone:Optional[str]=None, mobile_phone:Optional[str]=None, location:Optional[str]=None, password:Optional[str]=None, active:Optional[bool]=None
- endpoint: `{api_url}/table/sys_user/{params.user_id}`
- methods: PATCH

### update_workflow
- impl: `tools/workflow_tools.py:519` | params_model: `UpdateWorkflowParams`
- desc: Update an existing workflow in ServiceNow
- params: workflow_id:str, name:Optional[str]=None, description:Optional[str]=None, table:Optional[str]=None, active:Optional[bool]=None, attributes:Optional[Dict[str, Any]]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_workflow/{workflow_id}`
- methods: PATCH

### update_workflow_activity
- impl: `tools/workflow_tools.py:776` | params_model: `UpdateWorkflowActivityParams`
- desc: Update an existing activity in a workflow
- params: activity_id:str, name:Optional[str]=None, description:Optional[str]=None, attributes:Optional[Dict[str, Any]]=None
- endpoint: `{server_config.instance_url}/api/now/table/wf_activity/{activity_id}`
- methods: PATCH
