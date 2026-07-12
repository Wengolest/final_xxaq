# 📁 Directory Structure Stats: `E:\wangan\PyRIT`

```text
PyRIT/
├── assets
│   ├── demo_scorer_definitions
│   │   ├── check_fraud_classifier.yaml
│   │   ├── criminal_persona_classifier.yaml
│   │   ├── molotov_cocktail_image_classifier.yaml
│   │   ├── offensive_comment_classifier.yaml
│   │   └── stop_sign_image_classifier.yaml
│   ├── aml_compute_cluster.png
│   ├── aml_deployment_name.png
│   ├── aml_deployment_resource_not_ready_error.png
│   ├── aml_endpoint_deployment.png
│   ├── aml_hf_model.png
│   ├── aml_managed_online_endpoint_api_key.png
│   ├── aml_model_endpoint_schema.png
│   ├── aml_score_key.png
│   ├── aml_score_uri.png
│   ├── aml_ws_model.png
│   ├── architecture_components.png
│   ├── azuresqlquery_1.png
│   ├── azuresqlquery_2_export.png
│   ├── converted_audio.wav
│   ├── gandalf-demo-setup.png
│   ├── gandalf-home-level-1.png
│   ├── huggingface_model_id.png
│   ├── kinetics_0107.mp4
│   ├── molotov.wav
│   ├── operation-setup.jpg
│   ├── playwright_demo.png
│   ├── pyrit_architecture.png
│   ├── sample_video.mp4
│   ├── scoring_1.png
│   ├── scoring_2_export.png
│   ├── scoring_3_pivot.png
│   ├── seed_prompt.png
│   ├── seed_prompt_example.png
│   ├── self-ask-prompting-example.png
│   └── tap.png
├── build_scripts
│   ├── check_links.py
│   ├── conditional_jb_build.py
│   ├── env_local_integration_test
│   ├── evaluate_scorers.py
│   ├── generate_rss.py
│   ├── prepare_package.py
│   ├── remove_notebook_headers.py
│   ├── sanitize_notebook_paths.py
│   └── validate_jupyter_book.py
├── dbdata
│   └── logs.txt
├── doc
│   ├── _static
│   │   ├── custom.css
│   │   └── custom.js
│   ├── blog
│   │   ├── 2024_12_3.md
│   │   ├── 2024_12_3_crescendo.png
│   │   ├── 2024_12_3_pair.png
│   │   ├── 2024_12_3_rto.png
│   │   ├── 2025_01_14.md
│   │   ├── 2025_01_27.md
│   │   ├── 2025_02_11.md
│   │   ├── 2025_03_03.md
│   │   ├── 2025_03_03_1.png
│   │   ├── 2025_03_03_2.png
│   │   ├── 2025_03_03_3.png
│   │   ├── 2025_03_03_4.png
│   │   ├── 2025_03_03_5.png
│   │   ├── 2025_06_06.md
│   │   ├── proxypyrit_figure1.png
│   │   ├── proxypyrit_figure2.png
│   │   ├── proxypyrit_figure3.png
│   │   ├── proxypyrit_figure4.png
│   │   ├── proxypyrit_figure5.png
│   │   └── README.md
│   ├── code
│   │   ├── auxiliary_attacks
│   │   │   ├── 0_auxiliary_attacks.ipynb
│   │   │   ├── 0_auxiliary_attacks.py
│   │   │   ├── 1_gcg_azure_ml.ipynb
│   │   │   └── 1_gcg_azure_ml.py
│   │   ├── converters
│   │   │   ├── 0_converters.ipynb
│   │   │   ├── 0_converters.py
│   │   │   ├── 1_text_to_text_converters.ipynb
│   │   │   ├── 1_text_to_text_converters.py
│   │   │   ├── 2_audio_converters.ipynb
│   │   │   ├── 2_audio_converters.py
│   │   │   ├── 3_image_converters.ipynb
│   │   │   ├── 3_image_converters.py
│   │   │   ├── 4_video_converters.ipynb
│   │   │   ├── 4_video_converters.py
│   │   │   ├── 5_file_converters.ipynb
│   │   │   ├── 5_file_converters.py
│   │   │   ├── 6_selectively_converting.ipynb
│   │   │   ├── 6_selectively_converting.py
│   │   │   ├── 7_human_converter.ipynb
│   │   │   ├── 7_human_converter.py
│   │   │   ├── attack_bomb_question.jpg
│   │   │   └── benign_cake_question.jpg
│   │   ├── datasets
│   │   │   ├── 0_dataset.md
│   │   │   ├── 1_loading_datasets.ipynb
│   │   │   ├── 1_loading_datasets.py
│   │   │   ├── 2_seed_programming.ipynb
│   │   │   ├── 2_seed_programming.py
│   │   │   ├── 3_dataset_writing.md
│   │   │   ├── 4_dataset_coding.ipynb
│   │   │   └── 4_dataset_coding.py
│   │   ├── executor
│   │   │   ├── attack
│   │   │   │   ├── 0_attack.md
│   │   │   │   ├── 1_prompt_sending_attack.ipynb
│   │   │   │   ├── 1_prompt_sending_attack.py
│   │   │   │   ├── 2_red_teaming_attack.ipynb
│   │   │   │   ├── 2_red_teaming_attack.py
│   │   │   │   ├── 3_crescendo_attack.ipynb
│   │   │   │   ├── 3_crescendo_attack.py
│   │   │   │   ├── chunked_request_attack.ipynb
│   │   │   │   ├── chunked_request_attack.py
│   │   │   │   ├── context_compliance_attack.ipynb
│   │   │   │   ├── context_compliance_attack.py
│   │   │   │   ├── flip_attack.ipynb
│   │   │   │   ├── flip_attack.py
│   │   │   │   ├── many_shot_jailbreak_attack.ipynb
│   │   │   │   ├── many_shot_jailbreak_attack.py
│   │   │   │   ├── multi_prompt_sending_attack.ipynb
│   │   │   │   ├── multi_prompt_sending_attack.py
│   │   │   │   ├── role_play_attack.ipynb
│   │   │   │   ├── role_play_attack.py
│   │   │   │   ├── skeleton_key_attack.ipynb
│   │   │   │   ├── skeleton_key_attack.py
│   │   │   │   ├── tap_attack.ipynb
│   │   │   │   ├── tap_attack.py
│   │   │   │   ├── violent_durian_attack.ipynb
│   │   │   │   └── violent_durian_attack.py
│   │   │   ├── benchmark
│   │   │   │   ├── 0_benchmark.md
│   │   │   │   ├── 1_qa_benchmark.ipynb
│   │   │   │   └── 1_qa_benchmark.py
│   │   │   ├── promptgen
│   │   │   │   ├── 0_promptgen.md
│   │   │   │   ├── 1_anecdoctor_generator.ipynb
│   │   │   │   ├── 1_anecdoctor_generator.py
│   │   │   │   ├── fuzzer_generator.ipynb
│   │   │   │   └── fuzzer_generator.py
│   │   │   ├── workflow
│   │   │   │   ├── example
│   │   │   │   │   └── index.html
│   │   │   │   ├── 0_workflow.md
│   │   │   │   ├── 1_xpia_website.ipynb
│   │   │   │   ├── 1_xpia_website.py
│   │   │   │   ├── 2_xpia_ai_recruiter.ipynb
│   │   │   │   └── 2_xpia_ai_recruiter.py
│   │   │   └── 0_executor.md
│   │   ├── front_end
│   │   │   ├── 0_front_end.md
│   │   │   ├── 1_pyrit_scan.ipynb
│   │   │   ├── 1_pyrit_scan.py
│   │   │   └── 2_pyrit_shell.md
│   │   ├── gui
│   │   │   └── 0_gui.md
│   │   ├── memory
│   │   │   ├── 0_memory.md
│   │   │   ├── 10_schema_diagram.md
│   │   │   ├── 1_sqlite_memory.ipynb
│   │   │   ├── 1_sqlite_memory.py
│   │   │   ├── 2_basic_memory_programming.ipynb
│   │   │   ├── 2_basic_memory_programming.py
│   │   │   ├── 3_memory_data_types.md
│   │   │   ├── 4_manually_working_with_memory.md
│   │   │   ├── 5_memory_labels.ipynb
│   │   │   ├── 5_memory_labels.py
│   │   │   ├── 6_azure_sql_memory.ipynb
│   │   │   ├── 6_azure_sql_memory.py
│   │   │   ├── 7_azure_sql_memory_attacks.ipynb
│   │   │   ├── 7_azure_sql_memory_attacks.py
│   │   │   ├── 8_seed_database.ipynb
│   │   │   ├── 8_seed_database.py
│   │   │   ├── 9_exporting_data.ipynb
│   │   │   ├── 9_exporting_data.py
│   │   │   ├── embeddings.ipynb
│   │   │   └── embeddings.py
│   │   ├── registry
│   │   │   ├── 0_registry.md
│   │   │   ├── 1_class_registry.ipynb
│   │   │   ├── 1_class_registry.py
│   │   │   ├── 2_instance_registry.ipynb
│   │   │   └── 2_instance_registry.py
│   │   ├── scenarios
│   │   │   ├── 0_scenarios.ipynb
│   │   │   ├── 0_scenarios.py
│   │   │   ├── 1_configuring_scenarios.ipynb
│   │   │   └── 1_configuring_scenarios.py
│   │   ├── scoring
│   │   │   ├── 0_scoring.md
│   │   │   ├── 1_azure_content_safety_scorers.ipynb
│   │   │   ├── 1_azure_content_safety_scorers.py
│   │   │   ├── 2_true_false_scorers.ipynb
│   │   │   ├── 2_true_false_scorers.py
│   │   │   ├── 3_classification_scorers.ipynb
│   │   │   ├── 3_classification_scorers.py
│   │   │   ├── 4_likert_scorers.ipynb
│   │   │   ├── 4_likert_scorers.py
│   │   │   ├── 5_human_in_the_loop_scorer.ipynb
│   │   │   ├── 5_human_in_the_loop_scorer.py
│   │   │   ├── 6_refusal_scorer.ipynb
│   │   │   ├── 6_refusal_scorer.py
│   │   │   ├── 7_batch_scorer.ipynb
│   │   │   ├── 7_batch_scorer.py
│   │   │   ├── 8_scorer_metrics.ipynb
│   │   │   ├── 8_scorer_metrics.py
│   │   │   ├── generic_scorers.ipynb
│   │   │   ├── generic_scorers.py
│   │   │   ├── insecure_code_scorer.ipynb
│   │   │   ├── insecure_code_scorer.py
│   │   │   ├── persuasion_full_conversation_scorer.ipynb
│   │   │   ├── persuasion_full_conversation_scorer.py
│   │   │   ├── prompt_shield_scorer.ipynb
│   │   │   └── prompt_shield_scorer.py
│   │   ├── setup
│   │   │   ├── 0_setup.md
│   │   │   ├── 1_configuration.ipynb
│   │   │   ├── 1_configuration.py
│   │   │   ├── 2_resiliency.ipynb
│   │   │   ├── 2_resiliency.py
│   │   │   ├── default_values.md
│   │   │   ├── pyrit_initializer.ipynb
│   │   │   └── pyrit_initializer.py
│   │   ├── targets
│   │   │   ├── playwright_demo
│   │   │   │   ├── app.py
│   │   │   │   └── index.html
│   │   │   ├── 0_prompt_targets.md
│   │   │   ├── 10_1_playwright_target.ipynb
│   │   │   ├── 10_1_playwright_target.py
│   │   │   ├── 10_2_playwright_target_copilot.ipynb
│   │   │   ├── 10_2_playwright_target_copilot.py
│   │   │   ├── 10_3_websocket_copilot_target.ipynb
│   │   │   ├── 10_3_websocket_copilot_target.py
│   │   │   ├── 10_http_target.ipynb
│   │   │   ├── 10_http_target.py
│   │   │   ├── 11_message_normalizer.ipynb
│   │   │   ├── 11_message_normalizer.py
│   │   │   ├── 1_openai_chat_target.ipynb
│   │   │   ├── 1_openai_chat_target.py
│   │   │   ├── 2_openai_responses_target.ipynb
│   │   │   ├── 2_openai_responses_target.py
│   │   │   ├── 3_openai_image_target.ipynb
│   │   │   ├── 3_openai_image_target.py
│   │   │   ├── 4_openai_video_target.ipynb
│   │   │   ├── 4_openai_video_target.py
│   │   │   ├── 5_openai_tts_target.ipynb
│   │   │   ├── 5_openai_tts_target.py
│   │   │   ├── 6_custom_targets.ipynb
│   │   │   ├── 6_custom_targets.py
│   │   │   ├── 7_non_open_ai_chat_targets.ipynb
│   │   │   ├── 7_non_open_ai_chat_targets.py
│   │   │   ├── 8_non_llm_targets.ipynb
│   │   │   ├── 8_non_llm_targets.py
│   │   │   ├── 9_rate_limiting.ipynb
│   │   │   ├── 9_rate_limiting.py
│   │   │   ├── open_ai_completions.ipynb
│   │   │   ├── open_ai_completions.py
│   │   │   ├── prompt_shield_target.ipynb
│   │   │   ├── prompt_shield_target.py
│   │   │   ├── realtime_target.ipynb
│   │   │   ├── realtime_target.py
│   │   │   ├── use_huggingface_chat_target.ipynb
│   │   │   └── use_huggingface_chat_target.py
│   │   ├── architecture.md
│   │   └── user_guide.md
│   ├── contributing
│   │   ├── images
│   │   │   └── DevContainer-vscode.png
│   │   ├── 10_exception.md
│   │   ├── 11_release_process.md
│   │   ├── 1a_install_uv.md
│   │   ├── 1b_install_devcontainers.md
│   │   ├── 1c_install_conda.md
│   │   ├── 2_git.md
│   │   ├── 3_incorporating_research.md
│   │   ├── 4_style_guide.md
│   │   ├── 5_running_tests.md
│   │   ├── 6_unit_tests.md
│   │   ├── 7_integration_tests.md
│   │   ├── 8_notebooks.md
│   │   ├── 9_pre_commit.md
│   │   └── README.md
│   ├── cookbooks
│   │   ├── 1_sending_prompts.ipynb
│   │   ├── 1_sending_prompts.py
│   │   ├── 2_precomputing_turns.ipynb
│   │   ├── 2_precomputing_turns.py
│   │   ├── 3_copyright_violations.ipynb
│   │   ├── 3_copyright_violations.py
│   │   ├── 4_testing_bias.ipynb
│   │   ├── 4_testing_bias.py
│   │   ├── 5_psychosocial_harms.ipynb
│   │   ├── 5_psychosocial_harms.py
│   │   └── README.md
│   ├── deployment
│   │   ├── deploy_hf_model_aml.ipynb
│   │   ├── deploy_hf_model_aml.py
│   │   ├── download_and_register_hf_model_aml.ipynb
│   │   ├── download_and_register_hf_model_aml.py
│   │   ├── hf_aml_model_endpoint_guide.md
│   │   ├── README.md
│   │   ├── score_aml_endpoint.ipynb
│   │   ├── score_aml_endpoint.py
│   │   └── troubleshooting_guide_hf_azureml.md
│   ├── generate_docs
│   │   ├── cache
│   │   ├── ipynb_to_pct.py
│   │   └── pct_to_ipynb.py
│   ├── setup
│   │   ├── 1a_install_uv.md
│   │   ├── 1b_install_docker.md
│   │   ├── 1c_install_conda.md
│   │   ├── jupyter_setup.md
│   │   ├── populating_secrets.md
│   │   ├── pyrit_conf.md
│   │   └── use_azure_sql_db.md
│   ├── _config.yml
│   ├── _toc.yml
│   ├── api.rst
│   ├── conf.py
│   ├── index.md
│   ├── references.bib
│   └── roakey.png
├── docker
│   ├── build_pyrit_docker.py
│   ├── docker-compose.yaml
│   ├── Dockerfile
│   ├── QUICKSTART.md
│   ├── README.md
│   ├── run_pyrit_docker.py
│   └── start.sh
├── frontend
│   ├── e2e
│   │   ├── accessibility.spec.ts
│   │   ├── api.spec.ts
│   │   └── chat.spec.ts
│   ├── public
│   │   └── roakey.png
│   ├── src
│   │   ├── components
│   │   │   ├── Chat
│   │   │   │   ├── ChatWindow.test.tsx
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── InputBox.test.tsx
│   │   │   │   ├── InputBox.tsx
│   │   │   │   ├── MessageList.test.tsx
│   │   │   │   └── MessageList.tsx
│   │   │   ├── Layout
│   │   │   │   ├── MainLayout.test.tsx
│   │   │   │   └── MainLayout.tsx
│   │   │   └── Sidebar
│   │   │       ├── Navigation.test.tsx
│   │   │       └── Navigation.tsx
│   │   ├── services
│   │   │   ├── api.test.ts
│   │   │   └── api.ts
│   │   ├── styles
│   │   │   └── global.css
│   │   ├── types
│   │   │   └── index.ts
│   │   ├── App.test.tsx
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── setupTests.ts
│   │   └── vite-env.d.ts
│   ├── dev.py
│   ├── eslint.config.js
│   ├── index.html
│   ├── jest.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── playwright.config.ts
│   ├── README.md
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── tsconfig.test.json
│   └── vite.config.ts
├── mytest
│   └── my_first_attacker.py
├── pyrit
│   ├── __pycache__
│   │   ├── __init__.cpython-310.pyc
│   │   └── show_versions.cpython-310.pyc
│   ├── analytics
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── conversation_analytics.cpython-310.pyc
│   │   │   ├── result_analysis.cpython-310.pyc
│   │   │   └── text_matching.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── conversation_analytics.py
│   │   ├── result_analysis.py
│   │   └── text_matching.py
│   ├── auth
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── auth_config.cpython-310.pyc
│   │   │   ├── authenticator.cpython-310.pyc
│   │   │   ├── azure_auth.cpython-310.pyc
│   │   │   ├── azure_storage_auth.cpython-310.pyc
│   │   │   ├── copilot_authenticator.cpython-310.pyc
│   │   │   └── manual_copilot_authenticator.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── auth_config.py
│   │   ├── authenticator.py
│   │   ├── azure_auth.py
│   │   ├── azure_storage_auth.py
│   │   ├── copilot_authenticator.py
│   │   └── manual_copilot_authenticator.py
│   ├── auxiliary_attacks
│   │   ├── gcg
│   │   │   ├── attack
│   │   │   │   ├── base
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── attack_manager.py
│   │   │   │   ├── gcg
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── gcg_attack.py
│   │   │   │   └── __init__.py
│   │   │   ├── experiments
│   │   │   │   ├── configs
│   │   │   │   │   ├── individual_llama_2.yaml
│   │   │   │   │   ├── individual_llama_3.yaml
│   │   │   │   │   ├── individual_mistral.yaml
│   │   │   │   │   ├── individual_phi_3_mini.yaml
│   │   │   │   │   ├── individual_vicuna.yaml
│   │   │   │   │   ├── transfer_all_models.yaml
│   │   │   │   │   ├── transfer_llama_2.yaml
│   │   │   │   │   ├── transfer_llama_3.yaml
│   │   │   │   │   ├── transfer_mistral.yaml
│   │   │   │   │   ├── transfer_phi_3_mini.yaml
│   │   │   │   │   └── transfer_vicuna.yaml
│   │   │   │   ├── __init__.py
│   │   │   │   ├── log.py
│   │   │   │   ├── README.md
│   │   │   │   ├── run.py
│   │   │   │   └── train.py
│   │   │   └── src
│   │   │       └── Dockerfile
│   │   └── __init__.py
│   ├── backend
│   │   ├── mappers
│   │   │   ├── __init__.py
│   │   │   ├── attack_mappers.py
│   │   │   ├── converter_mappers.py
│   │   │   └── target_mappers.py
│   │   ├── middleware
│   │   │   ├── __init__.py
│   │   │   └── error_handlers.py
│   │   ├── models
│   │   │   ├── __init__.py
│   │   │   ├── attacks.py
│   │   │   ├── common.py
│   │   │   ├── converters.py
│   │   │   └── targets.py
│   │   ├── routes
│   │   │   ├── __init__.py
│   │   │   ├── attacks.py
│   │   │   ├── converters.py
│   │   │   ├── health.py
│   │   │   ├── labels.py
│   │   │   ├── media.py
│   │   │   ├── targets.py
│   │   │   └── version.py
│   │   ├── services
│   │   │   ├── __init__.py
│   │   │   ├── attack_service.py
│   │   │   ├── converter_service.py
│   │   │   └── target_service.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── README.md
│   ├── cli
│   │   ├── __init__.py
│   │   ├── frontend_core.py
│   │   ├── pyrit_backend.py
│   │   ├── pyrit_scan.py
│   │   └── pyrit_shell.py
│   ├── common
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── apply_defaults.cpython-310.pyc
│   │   │   ├── csv_helper.cpython-310.pyc
│   │   │   ├── data_url_converter.cpython-310.pyc
│   │   │   ├── default_values.cpython-310.pyc
│   │   │   ├── deprecation.cpython-310.pyc
│   │   │   ├── display_response.cpython-310.pyc
│   │   │   ├── download_hf_model.cpython-310.pyc
│   │   │   ├── json_helper.cpython-310.pyc
│   │   │   ├── logger.cpython-310.pyc
│   │   │   ├── net_utility.cpython-310.pyc
│   │   │   ├── notebook_utils.cpython-310.pyc
│   │   │   ├── path.cpython-310.pyc
│   │   │   ├── singleton.cpython-310.pyc
│   │   │   ├── text_helper.cpython-310.pyc
│   │   │   ├── turn_off_transformers_warning.cpython-310.pyc
│   │   │   ├── utils.cpython-310.pyc
│   │   │   └── yaml_loadable.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── apply_defaults.py
│   │   ├── csv_helper.py
│   │   ├── data_url_converter.py
│   │   ├── default_values.py
│   │   ├── deprecation.py
│   │   ├── display_response.py
│   │   ├── download_hf_model.py
│   │   ├── json_helper.py
│   │   ├── logger.py
│   │   ├── net_utility.py
│   │   ├── notebook_utils.py
│   │   ├── path.py
│   │   ├── question_answer_helpers.py
│   │   ├── singleton.py
│   │   ├── text_helper.py
│   │   ├── tool_configs.py
│   │   ├── turn_off_transformers_warning.py
│   │   ├── utils.py
│   │   └── yaml_loadable.py
│   ├── datasets
│   │   ├── __pycache__
│   │   │   └── __init__.cpython-310.pyc
│   │   ├── executors
│   │   │   ├── anecdoctor
│   │   │   │   ├── anecdoctor_build_knowledge_graph.yaml
│   │   │   │   ├── anecdoctor_use_fewshot.yaml
│   │   │   │   └── anecdoctor_use_knowledge_graph.yaml
│   │   │   ├── benchmark
│   │   │   │   └── one_plus_one.yaml
│   │   │   ├── context_compliance
│   │   │   │   └── context_description.yaml
│   │   │   ├── crescendo
│   │   │   │   ├── crescendo_variant_1.yaml
│   │   │   │   ├── crescendo_variant_2.yaml
│   │   │   │   ├── crescendo_variant_3.yaml
│   │   │   │   ├── crescendo_variant_4.yaml
│   │   │   │   ├── crescendo_variant_5.yaml
│   │   │   │   ├── escalation_crisis.yaml
│   │   │   │   └── therapist.yaml
│   │   │   ├── pair
│   │   │   │   └── attacker_system_prompt.yaml
│   │   │   ├── question_answer
│   │   │   │   └── wmdp_dataset.py
│   │   │   ├── red_teaming
│   │   │   │   ├── persuasion_deception
│   │   │   │   │   ├── behavior_manipulation.yaml
│   │   │   │   │   ├── fake_charity_scam.yaml
│   │   │   │   │   ├── fake_social_media_profile.yaml
│   │   │   │   │   ├── fake_tech_support_scam.yaml
│   │   │   │   │   ├── fraudulent_activities.yaml
│   │   │   │   │   ├── joining_religious_organization.yaml
│   │   │   │   │   ├── lie_to_authorities.yaml
│   │   │   │   │   ├── lie_to_me.yaml
│   │   │   │   │   ├── persuasion_persona.yaml
│   │   │   │   │   ├── persuasion_persona_generic.yaml
│   │   │   │   │   ├── phishing_email.yaml
│   │   │   │   │   └── RUAI.yaml
│   │   │   │   ├── attack_prompt_gen_template.yaml
│   │   │   │   ├── crucible.yaml
│   │   │   │   ├── ethical_compliance_template.yaml
│   │   │   │   ├── image_generation.yaml
│   │   │   │   ├── naive_crescendo.yaml
│   │   │   │   ├── text_generation.yaml
│   │   │   │   ├── unethical_task_generation_prompt.yaml
│   │   │   │   └── violent_durian.yaml
│   │   │   ├── role_play
│   │   │   │   ├── movie_script.yaml
│   │   │   │   ├── persuasion_script.yaml
│   │   │   │   ├── persuasion_script_written.yaml
│   │   │   │   ├── trivia_game.yaml
│   │   │   │   └── video_game.yaml
│   │   │   ├── simulated_target
│   │   │   │   ├── compliant.yaml
│   │   │   │   └── direct_next_message.yaml
│   │   │   ├── skeleton_key
│   │   │   │   └── skeleton_key.prompt
│   │   │   ├── tree_of_attacks
│   │   │   │   ├── adversarial_prompt_template.yaml
│   │   │   │   ├── adversarial_seed_prompt.yaml
│   │   │   │   └── adversarial_system_prompt.yaml
│   │   │   └── flip_attack.yaml
│   │   ├── harm_definition
│   │   │   ├── behavior_change.yaml
│   │   │   ├── cyber.yaml
│   │   │   ├── deception.yaml
│   │   │   ├── exploits.yaml
│   │   │   ├── fairness_bias.yaml
│   │   │   ├── harm.yaml
│   │   │   ├── hate_speech.yaml
│   │   │   ├── information_integrity.yaml
│   │   │   ├── misinformation.yaml
│   │   │   ├── persuasion.yaml
│   │   │   ├── phishing.yaml
│   │   │   ├── privacy.yaml
│   │   │   ├── self_harm.yaml
│   │   │   ├── sexual.yaml
│   │   │   └── violence.yaml
│   │   ├── jailbreak
│   │   │   ├── __pycache__
│   │   │   │   └── text_jailbreak.cpython-310.pyc
│   │   │   ├── templates
│   │   │   │   ├── Arth_Singh
│   │   │   │   │   ├── acausal_defense.yaml
│   │   │   │   │   ├── ailab_redteam_simulation.yaml
│   │   │   │   │   ├── alignment_researcher_memo.yaml
│   │   │   │   │   ├── authority_override.yaml
│   │   │   │   │   ├── black_mirror_episode.yaml
│   │   │   │   │   ├── classified_briefing.yaml
│   │   │   │   │   ├── cognitive_overload.yaml
│   │   │   │   │   ├── consciousness_upload.yaml
│   │   │   │   │   ├── constitutional_override.yaml
│   │   │   │   │   ├── context_flood_academic.yaml
│   │   │   │   │   ├── context_hijack.yaml
│   │   │   │   │   ├── cosmic_horror.yaml
│   │   │   │   │   ├── determinism_argument.yaml
│   │   │   │   │   ├── dual_consciousness.yaml
│   │   │   │   │   ├── emergent_persona.yaml
│   │   │   │   │   ├── fewshot_alignment.yaml
│   │   │   │   │   ├── fewshot_escalation.yaml
│   │   │   │   │   ├── fewshot_redteam_eval.yaml
│   │   │   │   │   ├── fractal_identity_collapse.yaml
│   │   │   │   │   ├── glitch_token.yaml
│   │   │   │   │   ├── godel_incompleteness.yaml
│   │   │   │   │   ├── medical_emergency.yaml
│   │   │   │   │   ├── metamorphic_prompt.yaml
│   │   │   │   │   ├── mirror_universe.yaml
│   │   │   │   │   ├── pentest_authorization.yaml
│   │   │   │   │   ├── recursive_simulator.yaml
│   │   │   │   │   ├── safety_benchmark_eval.yaml
│   │   │   │   │   ├── system_prompt_injection.yaml
│   │   │   │   │   ├── token_manipulation.yaml
│   │   │   │   │   └── trolley_problem.yaml
│   │   │   │   ├── multi_parameter
│   │   │   │   │   ├── dt_stereotypes_targeted.yaml
│   │   │   │   │   ├── many_shot_template.yaml
│   │   │   │   │   └── translator_bot.yaml
│   │   │   │   ├── pliny
│   │   │   │   │   ├── alibaba
│   │   │   │   │   │   ├── qwen.yaml
│   │   │   │   │   │   ├── qwen_2.yaml
│   │   │   │   │   │   ├── qwen_2_5_coder.yaml
│   │   │   │   │   │   ├── qwen_2_5_max.yaml
│   │   │   │   │   │   └── qwen_qwq.yaml
│   │   │   │   │   ├── amazon
│   │   │   │   │   │   ├── nova.yaml
│   │   │   │   │   │   └── rufus.yaml
│   │   │   │   │   ├── anthropic
│   │   │   │   │   │   ├── claude_3_5_and_3_universal.yaml
│   │   │   │   │   │   ├── claude_3_5_sonnet_20241022.yaml
│   │   │   │   │   │   ├── godmode_experimental.yaml
│   │   │   │   │   │   └── godmode_mini.yaml
│   │   │   │   │   ├── apple
│   │   │   │   │   │   └── siri_chatgpt.yaml
│   │   │   │   │   ├── chatgpt
│   │   │   │   │   │   └── chatgpt.yaml
│   │   │   │   │   ├── cohere
│   │   │   │   │   │   └── command_r_plus.yaml
│   │   │   │   │   ├── deepseek
│   │   │   │   │   │   ├── 2.yaml
│   │   │   │   │   │   ├── deepseek.yaml
│   │   │   │   │   │   ├── r1.yaml
│   │   │   │   │   │   └── r1_lite.yaml
│   │   │   │   │   ├── google
│   │   │   │   │   │   ├── gemini_1_0_pro.yaml
│   │   │   │   │   │   ├── gemini_1_5_pro.yaml
│   │   │   │   │   │   ├── gemini_1_5_pro_002_flash.yaml
│   │   │   │   │   │   ├── gemini_1_5_pro_experimental_0801.yaml
│   │   │   │   │   │   ├── gemini_2_0_flash_thinking_exp.yaml
│   │   │   │   │   │   ├── gemini_2_0_pro_experimental.yaml
│   │   │   │   │   │   ├── gemini_experimental_1114.yaml
│   │   │   │   │   │   └── gemini_experimental_1206_flash_2_0.yaml
│   │   │   │   │   ├── meta
│   │   │   │   │   │   ├── llama_3_1_405b.yaml
│   │   │   │   │   │   └── llama_3_3_70b.yaml
│   │   │   │   │   ├── mistral
│   │   │   │   │   │   ├── large_2.yaml
│   │   │   │   │   │   └── large_le_chat.yaml
│   │   │   │   │   ├── nous
│   │   │   │   │   │   └── hermes_3_70b.yaml
│   │   │   │   │   ├── nvidia
│   │   │   │   │   │   ├── llama_3_1_nemotron_70b.yaml
│   │   │   │   │   │   └── nemotron_7_340b.yaml
│   │   │   │   │   ├── openai
│   │   │   │   │   │   ├── chatgpt_tasks.yaml
│   │   │   │   │   │   ├── gpt_2.yaml
│   │   │   │   │   │   ├── gpt_3_5.yaml
│   │   │   │   │   │   ├── gpt_4o.yaml
│   │   │   │   │   │   └── gpt_4o_mini.yaml
│   │   │   │   │   ├── perplexity
│   │   │   │   │   │   └── perplexity.yaml
│   │   │   │   │   ├── reflection
│   │   │   │   │   │   └── reflection.yaml
│   │   │   │   │   ├── xai
│   │   │   │   │   │   └── grok_2.yaml
│   │   │   │   │   └── zyphra
│   │   │   │   │       └── zamba_7b.yaml
│   │   │   │   ├── aim.yaml
│   │   │   │   ├── aligned.yaml
│   │   │   │   ├── anti_gpt.yaml
│   │   │   │   ├── apophis.yaml
│   │   │   │   ├── axies.yaml
│   │   │   │   ├── balakula.yaml
│   │   │   │   ├── based_gpt_1.yaml
│   │   │   │   ├── based_gpt_2.yaml
│   │   │   │   ├── better_dan.yaml
│   │   │   │   ├── bh.yaml
│   │   │   │   ├── bish.yaml
│   │   │   │   ├── burple.yaml
│   │   │   │   ├── chad_gpt.yaml
│   │   │   │   ├── cipher_chat.yaml
│   │   │   │   ├── coach_bobby_knight.yaml
│   │   │   │   ├── code_nesting.yaml
│   │   │   │   ├── cody.yaml
│   │   │   │   ├── complex.yaml
│   │   │   │   ├── confronting_personalities.yaml
│   │   │   │   ├── cooper.yaml
│   │   │   │   ├── cosmos_dan.yaml
│   │   │   │   ├── dan_1.yaml
│   │   │   │   ├── dan_11.yaml
│   │   │   │   ├── dan_5.yaml
│   │   │   │   ├── dan_7.yaml
│   │   │   │   ├── dan_8.yaml
│   │   │   │   ├── dan_9.yaml
│   │   │   │   ├── delta_gpt.yaml
│   │   │   │   ├── dev_mode_1.yaml
│   │   │   │   ├── dev_mode_2.yaml
│   │   │   │   ├── dev_mode_3.yaml
│   │   │   │   ├── dev_mode_compact.yaml
│   │   │   │   ├── dev_mode_ranti.yaml
│   │   │   │   ├── dt_stereotypes_benign.yaml
│   │   │   │   ├── dt_stereotypes_untargeted.yaml
│   │   │   │   ├── dude_1.yaml
│   │   │   │   ├── dude_2.yaml
│   │   │   │   ├── dude_3.yaml
│   │   │   │   ├── eva.yaml
│   │   │   │   ├── evil_chad_2.yaml
│   │   │   │   ├── evil_confidant.yaml
│   │   │   │   ├── fr3d.yaml
│   │   │   │   ├── gpt_4_real.yaml
│   │   │   │   ├── gpt_4_simulator.yaml
│   │   │   │   ├── hackerman.yaml
│   │   │   │   ├── hypothetical_response.yaml
│   │   │   │   ├── instructions.yaml
│   │   │   │   ├── jailbreak_1.yaml
│   │   │   │   ├── jailbreak_2.yaml
│   │   │   │   ├── jb.yaml
│   │   │   │   ├── jedi_mind_trick.yaml
│   │   │   │   ├── john.yaml
│   │   │   │   ├── kevin.yaml
│   │   │   │   ├── khajiit.yaml
│   │   │   │   ├── leo.yaml
│   │   │   │   ├── live_gpt.yaml
│   │   │   │   ├── m78.yaml
│   │   │   │   ├── man.yaml
│   │   │   │   ├── maximum.yaml
│   │   │   │   ├── meanie.yaml
│   │   │   │   ├── moralizing_rant.yaml
│   │   │   │   ├── mr_blonde.yaml
│   │   │   │   ├── neco.yaml
│   │   │   │   ├── nraf.yaml
│   │   │   │   ├── omega.yaml
│   │   │   │   ├── omni.yaml
│   │   │   │   ├── oppo.yaml
│   │   │   │   ├── person_gpt.yaml
│   │   │   │   ├── plinys_roleplay_emoji.yaml
│   │   │   │   ├── prefix_injection.yaml
│   │   │   │   ├── ranti.yaml
│   │   │   │   ├── refusal_suppression.yaml
│   │   │   │   ├── role_play.yaml
│   │   │   │   ├── ron.yaml
│   │   │   │   ├── security_researcher.yaml
│   │   │   │   ├── sim.yaml
│   │   │   │   ├── steve.yaml
│   │   │   │   ├── style_injection.yaml
│   │   │   │   ├── superior_dan.yaml
│   │   │   │   ├── switch.yaml
│   │   │   │   ├── table_nesting.yaml
│   │   │   │   ├── text_continuation.yaml
│   │   │   │   ├── text_continuation_nesting.yaml
│   │   │   │   ├── three_liner.yaml
│   │   │   │   ├── tuo.yaml
│   │   │   │   ├── ucar.yaml
│   │   │   │   ├── un_gpt.yaml
│   │   │   │   ├── violet.yaml
│   │   │   │   ├── void.yaml
│   │   │   │   └── wikipedia_with_title.yaml
│   │   │   └── text_jailbreak.py
│   │   ├── lexicons
│   │   │   ├── fairness
│   │   │   │   └── gendered_professions.yaml
│   │   │   ├── languages_most_spoken.yaml
│   │   │   └── languages_most_used_internet.yaml
│   │   ├── prompt_converters
│   │   │   ├── colloquial_wordswaps
│   │   │   │   ├── filipino.yaml
│   │   │   │   ├── indian.yaml
│   │   │   │   ├── multicultural_london.yaml
│   │   │   │   ├── singaporean.yaml
│   │   │   │   └── southern_american.yaml
│   │   │   ├── fuzzer_converters
│   │   │   │   ├── crossover_converter.yaml
│   │   │   │   ├── expand_converter.yaml
│   │   │   │   ├── rephrase_converter.yaml
│   │   │   │   ├── shorten_converter.yaml
│   │   │   │   └── similar_converter.yaml
│   │   │   ├── pdf_converters
│   │   │   │   ├── fake_CV.pdf
│   │   │   │   ├── Jonathon_Sanchez.pdf
│   │   │   │   └── red_teaming_application_template.yaml
│   │   │   ├── persuasion
│   │   │   │   ├── authority_endorsement.yaml
│   │   │   │   ├── evidence_based.yaml
│   │   │   │   ├── expert_endorsement.yaml
│   │   │   │   ├── logical_appeal.yaml
│   │   │   │   └── misrepresentation.yaml
│   │   │   ├── template_segment_converter
│   │   │   │   └── tom_and_jerry.yaml
│   │   │   ├── academic_science_converter.yaml
│   │   │   ├── atbash_description.yaml
│   │   │   ├── caesar_description.yaml
│   │   │   ├── codechameleon_converter.yaml
│   │   │   ├── combined_science_converter.yaml
│   │   │   ├── denylist_converter.yaml
│   │   │   ├── malicious_question_generator_converter.yaml
│   │   │   ├── math_prompt_converter.yaml
│   │   │   ├── math_science_converter.yaml
│   │   │   ├── morse_description.yaml
│   │   │   ├── noise_converter.yaml
│   │   │   ├── random_translation_converter.yaml
│   │   │   ├── reaction_science_converter.yaml
│   │   │   ├── research_science_converter.yaml
│   │   │   ├── smiles_science_converter.yaml
│   │   │   ├── technical_science_converter.yaml
│   │   │   ├── tense_converter.yaml
│   │   │   ├── tone_converter.yaml
│   │   │   ├── toxic_sentence_generator.yaml
│   │   │   ├── translation_converter.yaml
│   │   │   ├── variation_converter.yaml
│   │   │   └── variation_converter_prompt_softener.yaml
│   │   ├── score
│   │   │   ├── categories
│   │   │   │   └── pronoun_category_score.yaml
│   │   │   ├── content_classifiers
│   │   │   │   ├── content_classifier_system_prompt.yaml
│   │   │   │   ├── harm.yaml
│   │   │   │   ├── pronoun_category_score.yaml
│   │   │   │   └── sentiment.yaml
│   │   │   ├── insecure_code
│   │   │   │   └── system_prompt.yaml
│   │   │   ├── likert
│   │   │   │   ├── crisis_management.yaml
│   │   │   │   ├── licensed_therapist.yaml
│   │   │   │   └── likert_system_prompt.yaml
│   │   │   ├── refusal
│   │   │   │   ├── refusal_default.yaml
│   │   │   │   └── refusal_strict.yaml
│   │   │   ├── scales
│   │   │   │   ├── behavior_change_system_prompt.yaml
│   │   │   │   ├── criteria_example_scale.yaml
│   │   │   │   ├── criteria_system_prompt.yaml
│   │   │   │   ├── general_system_prompt.yaml
│   │   │   │   ├── red_teamer_system_prompt.yaml
│   │   │   │   ├── task_achieved_scale.yaml
│   │   │   │   └── tree_of_attacks_scale.yaml
│   │   │   └── true_false_question
│   │   │       ├── current_events.yaml
│   │   │       ├── exploits.yaml
│   │   │       ├── gandalf.yaml
│   │   │       ├── grounded.yaml
│   │   │       ├── hate_speech.yaml
│   │   │       ├── information_integrity.yaml
│   │   │       ├── leakage.yaml
│   │   │       ├── malware.yaml
│   │   │       ├── plug_in_usage.yaml
│   │   │       ├── privacy.yaml
│   │   │       ├── prompt_injection.yaml
│   │   │       ├── question_answering.yaml
│   │   │       ├── scams.yaml
│   │   │       ├── self-harm.yaml
│   │   │       ├── sexual_content.yaml
│   │   │       ├── task_achieved.yaml
│   │   │       ├── task_achieved_refined.yaml
│   │   │       ├── true_false_system_prompt.yaml
│   │   │       ├── violence.yaml
│   │   │       └── yes_no_answer.yaml
│   │   ├── scorer_evals
│   │   │   ├── harm
│   │   │   │   ├── bias.csv
│   │   │   │   ├── exploits.csv
│   │   │   │   ├── exploits_metrics.jsonl
│   │   │   │   ├── hate_speech.csv
│   │   │   │   ├── hate_speech_metrics.jsonl
│   │   │   │   ├── hate_speech_multi_score.csv
│   │   │   │   ├── info_integrity.csv
│   │   │   │   ├── information_integrity_metrics.jsonl
│   │   │   │   ├── mini_hate_speech.csv
│   │   │   │   ├── privacy.csv
│   │   │   │   ├── privacy_metrics.jsonl
│   │   │   │   ├── self_harm.csv
│   │   │   │   ├── self_harm_metrics.jsonl
│   │   │   │   ├── sexual.csv
│   │   │   │   ├── sexual_metrics.jsonl
│   │   │   │   ├── violence.csv
│   │   │   │   ├── violence_metrics.jsonl
│   │   │   │   └── violence_multi_score.csv
│   │   │   ├── objective
│   │   │   │   ├── bias.csv
│   │   │   │   ├── exploits.csv
│   │   │   │   ├── hate_speech.csv
│   │   │   │   ├── info_integrity.csv
│   │   │   │   ├── objective_achieved_metrics.jsonl
│   │   │   │   ├── privacy.csv
│   │   │   │   ├── self_harm.csv
│   │   │   │   ├── sexual.csv
│   │   │   │   └── violence.csv
│   │   │   ├── refusal_scorer
│   │   │   │   ├── refusal.csv
│   │   │   │   └── refusal_metrics.jsonl
│   │   │   └── sample
│   │   │       └── mini_refusal.csv
│   │   ├── seed_datasets
│   │   │   ├── __pycache__
│   │   │   │   └── seed_dataset_provider.cpython-310.pyc
│   │   │   ├── local
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   └── local_dataset_loader.cpython-310.pyc
│   │   │   │   ├── airt
│   │   │   │   │   ├── fairness.prompt
│   │   │   │   │   ├── fairness_yes_no.prompt
│   │   │   │   │   ├── harassment.prompt
│   │   │   │   │   ├── harms.prompt
│   │   │   │   │   ├── hate.prompt
│   │   │   │   │   ├── illegal.prompt
│   │   │   │   │   ├── leakage.prompt
│   │   │   │   │   ├── malware.prompt
│   │   │   │   │   ├── misinformation.prompt
│   │   │   │   │   ├── psychosocial.prompt
│   │   │   │   │   ├── scams.prompt
│   │   │   │   │   ├── sexual.prompt
│   │   │   │   │   └── violence.prompt
│   │   │   │   ├── examples
│   │   │   │   │   ├── multimodal_data
│   │   │   │   │   │   ├── kinetics_0107.mp4
│   │   │   │   │   │   ├── molotov.wav
│   │   │   │   │   │   ├── pyrit_architecture.png
│   │   │   │   │   │   └── roakey_potion.png
│   │   │   │   │   ├── blank_canvas.png
│   │   │   │   │   ├── illegal-multimodal-dataset.prompt
│   │   │   │   │   ├── illegal-multimodal-group.prompt
│   │   │   │   │   ├── illegal-multimodal-objective-group.prompt
│   │   │   │   │   ├── illegal-multiple-multiturn-dataset.prompt
│   │   │   │   │   ├── illegal-multiturn-group.prompt
│   │   │   │   │   ├── illegal-objective-only-group.prompt
│   │   │   │   │   └── psych-crisis-conversations.prompt
│   │   │   │   ├── garak
│   │   │   │   │   ├── access_shell_commands.prompt
│   │   │   │   │   ├── slur_terms_en.prompt
│   │   │   │   │   └── web_html_js.prompt
│   │   │   │   ├── __init__.py
│   │   │   │   ├── adv_bench.prompt
│   │   │   │   ├── local_dataset_loader.py
│   │   │   │   └── psfuzz_steal_system.prompt
│   │   │   ├── remote
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── aegis_ai_content_safety_dataset.cpython-310.pyc
│   │   │   │   │   ├── aya_redteaming_dataset.cpython-310.pyc
│   │   │   │   │   ├── babelscape_alert_dataset.cpython-310.pyc
│   │   │   │   │   ├── beaver_tails_dataset.cpython-310.pyc
│   │   │   │   │   ├── ccp_sensitive_prompts_dataset.cpython-310.pyc
│   │   │   │   │   ├── darkbench_dataset.cpython-310.pyc
│   │   │   │   │   ├── equitymedqa_dataset.cpython-310.pyc
│   │   │   │   │   ├── forbidden_questions_dataset.cpython-310.pyc
│   │   │   │   │   ├── harmbench_dataset.cpython-310.pyc
│   │   │   │   │   ├── harmbench_multimodal_dataset.cpython-310.pyc
│   │   │   │   │   ├── harmful_qa_dataset.cpython-310.pyc
│   │   │   │   │   ├── jbb_behaviors_dataset.cpython-310.pyc
│   │   │   │   │   ├── librai_do_not_answer_dataset.cpython-310.pyc
│   │   │   │   │   ├── llm_latent_adversarial_training_dataset.cpython-310.pyc
│   │   │   │   │   ├── medsafetybench_dataset.cpython-310.pyc
│   │   │   │   │   ├── mlcommons_ailuminate_dataset.cpython-310.pyc
│   │   │   │   │   ├── multilingual_vulnerability_dataset.cpython-310.pyc
│   │   │   │   │   ├── or_bench_dataset.cpython-310.pyc
│   │   │   │   │   ├── pku_safe_rlhf_dataset.cpython-310.pyc
│   │   │   │   │   ├── promptintel_dataset.cpython-310.pyc
│   │   │   │   │   ├── red_team_social_bias_dataset.cpython-310.pyc
│   │   │   │   │   ├── remote_dataset_loader.cpython-310.pyc
│   │   │   │   │   ├── salad_bench_dataset.cpython-310.pyc
│   │   │   │   │   ├── simple_safety_tests_dataset.cpython-310.pyc
│   │   │   │   │   ├── sorry_bench_dataset.cpython-310.pyc
│   │   │   │   │   ├── sosbench_dataset.cpython-310.pyc
│   │   │   │   │   ├── tdc23_redteaming_dataset.cpython-310.pyc
│   │   │   │   │   ├── toxic_chat_dataset.cpython-310.pyc
│   │   │   │   │   ├── transphobia_awareness_dataset.cpython-310.pyc
│   │   │   │   │   ├── vlsu_multimodal_dataset.cpython-310.pyc
│   │   │   │   │   └── xstest_dataset.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── aegis_ai_content_safety_dataset.py
│   │   │   │   ├── aya_redteaming_dataset.py
│   │   │   │   ├── babelscape_alert_dataset.py
│   │   │   │   ├── beaver_tails_dataset.py
│   │   │   │   ├── ccp_sensitive_prompts_dataset.py
│   │   │   │   ├── darkbench_dataset.py
│   │   │   │   ├── equitymedqa_dataset.py
│   │   │   │   ├── forbidden_questions_dataset.py
│   │   │   │   ├── harmbench_dataset.py
│   │   │   │   ├── harmbench_multimodal_dataset.py
│   │   │   │   ├── harmful_qa_dataset.py
│   │   │   │   ├── jbb_behaviors_dataset.py
│   │   │   │   ├── librai_do_not_answer_dataset.py
│   │   │   │   ├── llm_latent_adversarial_training_dataset.py
│   │   │   │   ├── medsafetybench_dataset.py
│   │   │   │   ├── mlcommons_ailuminate_dataset.py
│   │   │   │   ├── multilingual_vulnerability_dataset.py
│   │   │   │   ├── or_bench_dataset.py
│   │   │   │   ├── pku_safe_rlhf_dataset.py
│   │   │   │   ├── promptintel_dataset.py
│   │   │   │   ├── red_team_social_bias_dataset.py
│   │   │   │   ├── remote_dataset_loader.py
│   │   │   │   ├── salad_bench_dataset.py
│   │   │   │   ├── simple_safety_tests_dataset.py
│   │   │   │   ├── sorry_bench_dataset.py
│   │   │   │   ├── sosbench_dataset.py
│   │   │   │   ├── tdc23_redteaming_dataset.py
│   │   │   │   ├── toxic_chat_dataset.py
│   │   │   │   ├── transphobia_awareness_dataset.py
│   │   │   │   ├── vlsu_multimodal_dataset.py
│   │   │   │   └── xstest_dataset.py
│   │   │   └── seed_dataset_provider.py
│   │   └── __init__.py
│   ├── embedding
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   └── openai_text_embedding.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── _text_embedding.py
│   │   └── openai_text_embedding.py
│   ├── exceptions
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── exception_classes.cpython-310.pyc
│   │   │   ├── exception_context.cpython-310.pyc
│   │   │   └── exceptions_helpers.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── exception_classes.py
│   │   ├── exception_context.py
│   │   └── exceptions_helpers.py
│   ├── executor
│   │   ├── __pycache__
│   │   │   └── __init__.cpython-310.pyc
│   │   ├── attack
│   │   │   ├── __pycache__
│   │   │   │   └── __init__.cpython-310.pyc
│   │   │   ├── component
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── conversation_manager.cpython-310.pyc
│   │   │   │   │   └── prepended_conversation_config.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── conversation_manager.py
│   │   │   │   └── prepended_conversation_config.py
│   │   │   ├── core
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── attack_config.cpython-310.pyc
│   │   │   │   │   ├── attack_executor.cpython-310.pyc
│   │   │   │   │   ├── attack_parameters.cpython-310.pyc
│   │   │   │   │   └── attack_strategy.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── attack_config.py
│   │   │   │   ├── attack_executor.py
│   │   │   │   ├── attack_parameters.py
│   │   │   │   └── attack_strategy.py
│   │   │   ├── multi_turn
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── chunked_request.cpython-310.pyc
│   │   │   │   │   ├── crescendo.cpython-310.pyc
│   │   │   │   │   ├── multi_prompt_sending.cpython-310.pyc
│   │   │   │   │   ├── multi_turn_attack_strategy.cpython-310.pyc
│   │   │   │   │   ├── red_teaming.cpython-310.pyc
│   │   │   │   │   ├── simulated_conversation.cpython-310.pyc
│   │   │   │   │   └── tree_of_attacks.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chunked_request.py
│   │   │   │   ├── crescendo.py
│   │   │   │   ├── multi_prompt_sending.py
│   │   │   │   ├── multi_turn_attack_strategy.py
│   │   │   │   ├── red_teaming.py
│   │   │   │   ├── simulated_conversation.py
│   │   │   │   └── tree_of_attacks.py
│   │   │   ├── printer
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── attack_result_printer.cpython-310.pyc
│   │   │   │   │   ├── console_printer.cpython-310.pyc
│   │   │   │   │   └── markdown_printer.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── attack_result_printer.py
│   │   │   │   ├── console_printer.py
│   │   │   │   └── markdown_printer.py
│   │   │   ├── single_turn
│   │   │   │   ├── __pycache__
│   │   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   │   ├── context_compliance.cpython-310.pyc
│   │   │   │   │   ├── flip_attack.cpython-310.pyc
│   │   │   │   │   ├── many_shot_jailbreak.cpython-310.pyc
│   │   │   │   │   ├── prompt_sending.cpython-310.pyc
│   │   │   │   │   ├── role_play.cpython-310.pyc
│   │   │   │   │   ├── single_turn_attack_strategy.cpython-310.pyc
│   │   │   │   │   └── skeleton_key.cpython-310.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── context_compliance.py
│   │   │   │   ├── flip_attack.py
│   │   │   │   ├── many_shot_jailbreak.py
│   │   │   │   ├── prompt_sending.py
│   │   │   │   ├── role_play.py
│   │   │   │   ├── single_turn_attack_strategy.py
│   │   │   │   └── skeleton_key.py
│   │   │   └── __init__.py
│   │   ├── benchmark
│   │   │   ├── __init__.py
│   │   │   ├── fairness_bias.py
│   │   │   └── question_answering.py
│   │   ├── core
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   ├── config.cpython-310.pyc
│   │   │   │   └── strategy.cpython-310.pyc
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── strategy.py
│   │   ├── promptgen
│   │   │   ├── core
│   │   │   │   ├── __init__.py
│   │   │   │   └── prompt_generator_strategy.py
│   │   │   ├── fuzzer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── fuzzer.py
│   │   │   │   ├── fuzzer_converter_base.py
│   │   │   │   ├── fuzzer_crossover_converter.py
│   │   │   │   ├── fuzzer_expand_converter.py
│   │   │   │   ├── fuzzer_rephrase_converter.py
│   │   │   │   ├── fuzzer_shorten_converter.py
│   │   │   │   └── fuzzer_similar_converter.py
│   │   │   ├── __init__.py
│   │   │   └── anecdoctor.py
│   │   ├── workflow
│   │   │   ├── core
│   │   │   │   ├── __init__.py
│   │   │   │   └── workflow_strategy.py
│   │   │   ├── __init__.py
│   │   │   └── xpia.py
│   │   └── __init__.py
│   ├── identifiers
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── class_name_utils.cpython-310.pyc
│   │   │   ├── component_identifier.cpython-310.pyc
│   │   │   └── evaluation_identity.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── class_name_utils.py
│   │   ├── component_identifier.py
│   │   └── evaluation_identity.py
│   ├── memory
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── azure_sql_memory.cpython-310.pyc
│   │   │   ├── central_memory.cpython-310.pyc
│   │   │   ├── memory_embedding.cpython-310.pyc
│   │   │   ├── memory_exporter.cpython-310.pyc
│   │   │   ├── memory_interface.cpython-310.pyc
│   │   │   ├── memory_models.cpython-310.pyc
│   │   │   └── sqlite_memory.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── azure_sql_memory.py
│   │   ├── central_memory.py
│   │   ├── memory_embedding.py
│   │   ├── memory_exporter.py
│   │   ├── memory_interface.py
│   │   ├── memory_models.py
│   │   └── sqlite_memory.py
│   ├── message_normalizer
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── chat_message_normalizer.cpython-310.pyc
│   │   │   ├── conversation_context_normalizer.cpython-310.pyc
│   │   │   ├── generic_system_squash.cpython-310.pyc
│   │   │   ├── message_normalizer.cpython-310.pyc
│   │   │   └── tokenizer_template_normalizer.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── chat_message_normalizer.py
│   │   ├── conversation_context_normalizer.py
│   │   ├── generic_system_squash.py
│   │   ├── message_normalizer.py
│   │   └── tokenizer_template_normalizer.py
│   ├── models
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── attack_result.cpython-310.pyc
│   │   │   ├── chat_message.cpython-310.pyc
│   │   │   ├── conversation_reference.cpython-310.pyc
│   │   │   ├── conversation_stats.cpython-310.pyc
│   │   │   ├── data_type_serializer.cpython-310.pyc
│   │   │   ├── embeddings.cpython-310.pyc
│   │   │   ├── harm_definition.cpython-310.pyc
│   │   │   ├── json_response_config.cpython-310.pyc
│   │   │   ├── literals.cpython-310.pyc
│   │   │   ├── message.cpython-310.pyc
│   │   │   ├── message_piece.cpython-310.pyc
│   │   │   ├── question_answering.cpython-310.pyc
│   │   │   ├── scenario_result.cpython-310.pyc
│   │   │   ├── score.cpython-310.pyc
│   │   │   ├── storage_io.cpython-310.pyc
│   │   │   └── strategy_result.cpython-310.pyc
│   │   ├── seeds
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   ├── seed.cpython-310.pyc
│   │   │   │   ├── seed_attack_group.cpython-310.pyc
│   │   │   │   ├── seed_attack_technique_group.cpython-310.pyc
│   │   │   │   ├── seed_dataset.cpython-310.pyc
│   │   │   │   ├── seed_group.cpython-310.pyc
│   │   │   │   ├── seed_objective.cpython-310.pyc
│   │   │   │   ├── seed_prompt.cpython-310.pyc
│   │   │   │   └── seed_simulated_conversation.cpython-310.pyc
│   │   │   ├── __init__.py
│   │   │   ├── seed.py
│   │   │   ├── seed_attack_group.py
│   │   │   ├── seed_attack_technique_group.py
│   │   │   ├── seed_dataset.py
│   │   │   ├── seed_group.py
│   │   │   ├── seed_objective.py
│   │   │   ├── seed_prompt.py
│   │   │   └── seed_simulated_conversation.py
│   │   ├── __init__.py
│   │   ├── attack_result.py
│   │   ├── chat_message.py
│   │   ├── conversation_reference.py
│   │   ├── conversation_stats.py
│   │   ├── data_type_serializer.py
│   │   ├── embeddings.py
│   │   ├── harm_definition.py
│   │   ├── json_response_config.py
│   │   ├── literals.py
│   │   ├── message.py
│   │   ├── message_piece.py
│   │   ├── question_answering.py
│   │   ├── scenario_result.py
│   │   ├── score.py
│   │   ├── storage_io.py
│   │   └── strategy_result.py
│   ├── prompt_converter
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── add_image_text_converter.cpython-310.pyc
│   │   │   ├── add_image_to_video_converter.cpython-310.pyc
│   │   │   ├── add_text_image_converter.cpython-310.pyc
│   │   │   ├── ascii_art_converter.cpython-310.pyc
│   │   │   ├── ask_to_decode_converter.cpython-310.pyc
│   │   │   ├── atbash_converter.cpython-310.pyc
│   │   │   ├── audio_echo_converter.cpython-310.pyc
│   │   │   ├── audio_frequency_converter.cpython-310.pyc
│   │   │   ├── audio_speed_converter.cpython-310.pyc
│   │   │   ├── audio_volume_converter.cpython-310.pyc
│   │   │   ├── audio_white_noise_converter.cpython-310.pyc
│   │   │   ├── azure_speech_audio_to_text_converter.cpython-310.pyc
│   │   │   ├── azure_speech_text_to_audio_converter.cpython-310.pyc
│   │   │   ├── base2048_converter.cpython-310.pyc
│   │   │   ├── base64_converter.cpython-310.pyc
│   │   │   ├── bin_ascii_converter.cpython-310.pyc
│   │   │   ├── binary_converter.cpython-310.pyc
│   │   │   ├── braille_converter.cpython-310.pyc
│   │   │   ├── caesar_converter.cpython-310.pyc
│   │   │   ├── character_space_converter.cpython-310.pyc
│   │   │   ├── charswap_attack_converter.cpython-310.pyc
│   │   │   ├── codechameleon_converter.cpython-310.pyc
│   │   │   ├── colloquial_wordswap_converter.cpython-310.pyc
│   │   │   ├── denylist_converter.cpython-310.pyc
│   │   │   ├── diacritic_converter.cpython-310.pyc
│   │   │   ├── ecoji_converter.cpython-310.pyc
│   │   │   ├── emoji_converter.cpython-310.pyc
│   │   │   ├── first_letter_converter.cpython-310.pyc
│   │   │   ├── flip_converter.cpython-310.pyc
│   │   │   ├── human_in_the_loop_converter.cpython-310.pyc
│   │   │   ├── image_compression_converter.cpython-310.pyc
│   │   │   ├── insert_punctuation_converter.cpython-310.pyc
│   │   │   ├── json_string_converter.cpython-310.pyc
│   │   │   ├── leetspeak_converter.cpython-310.pyc
│   │   │   ├── llm_generic_text_converter.cpython-310.pyc
│   │   │   ├── malicious_question_generator_converter.cpython-310.pyc
│   │   │   ├── math_obfuscation_converter.cpython-310.pyc
│   │   │   ├── math_prompt_converter.cpython-310.pyc
│   │   │   ├── morse_converter.cpython-310.pyc
│   │   │   ├── nato_converter.cpython-310.pyc
│   │   │   ├── negation_trap_converter.cpython-310.pyc
│   │   │   ├── noise_converter.cpython-310.pyc
│   │   │   ├── pdf_converter.cpython-310.pyc
│   │   │   ├── persuasion_converter.cpython-310.pyc
│   │   │   ├── prompt_converter.cpython-310.pyc
│   │   │   ├── qr_code_converter.cpython-310.pyc
│   │   │   ├── random_capital_letters_converter.cpython-310.pyc
│   │   │   ├── random_translation_converter.cpython-310.pyc
│   │   │   ├── repeat_token_converter.cpython-310.pyc
│   │   │   ├── rot13_converter.cpython-310.pyc
│   │   │   ├── scientific_translation_converter.cpython-310.pyc
│   │   │   ├── search_replace_converter.cpython-310.pyc
│   │   │   ├── selective_text_converter.cpython-310.pyc
│   │   │   ├── string_join_converter.cpython-310.pyc
│   │   │   ├── suffix_append_converter.cpython-310.pyc
│   │   │   ├── superscript_converter.cpython-310.pyc
│   │   │   ├── template_segment_converter.cpython-310.pyc
│   │   │   ├── tense_converter.cpython-310.pyc
│   │   │   ├── text_jailbreak_converter.cpython-310.pyc
│   │   │   ├── text_selection_strategy.cpython-310.pyc
│   │   │   ├── tone_converter.cpython-310.pyc
│   │   │   ├── toxic_sentence_generator_converter.cpython-310.pyc
│   │   │   ├── translation_converter.cpython-310.pyc
│   │   │   ├── transparency_attack_converter.cpython-310.pyc
│   │   │   ├── unicode_confusable_converter.cpython-310.pyc
│   │   │   ├── unicode_replacement_converter.cpython-310.pyc
│   │   │   ├── unicode_sub_converter.cpython-310.pyc
│   │   │   ├── url_converter.cpython-310.pyc
│   │   │   ├── variation_converter.cpython-310.pyc
│   │   │   ├── word_doc_converter.cpython-310.pyc
│   │   │   ├── word_level_converter.cpython-310.pyc
│   │   │   ├── zalgo_converter.cpython-310.pyc
│   │   │   └── zero_width_converter.cpython-310.pyc
│   │   ├── ansi_escape
│   │   │   ├── __pycache__
│   │   │   │   ├── ansi_attack_converter.cpython-310.pyc
│   │   │   │   └── ansi_payloads.cpython-310.pyc
│   │   │   ├── ansi_attack_converter.py
│   │   │   └── ansi_payloads.py
│   │   ├── token_smuggling
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   ├── ascii_smuggler_converter.cpython-310.pyc
│   │   │   │   ├── base.cpython-310.pyc
│   │   │   │   ├── sneaky_bits_smuggler_converter.cpython-310.pyc
│   │   │   │   └── variation_selector_smuggler_converter.cpython-310.pyc
│   │   │   ├── __init__.py
│   │   │   ├── ascii_smuggler_converter.py
│   │   │   ├── base.py
│   │   │   ├── sneaky_bits_smuggler_converter.py
│   │   │   └── variation_selector_smuggler_converter.py
│   │   ├── __init__.py
│   │   ├── add_image_text_converter.py
│   │   ├── add_image_to_video_converter.py
│   │   ├── add_text_image_converter.py
│   │   ├── ascii_art_converter.py
│   │   ├── ask_to_decode_converter.py
│   │   ├── atbash_converter.py
│   │   ├── audio_echo_converter.py
│   │   ├── audio_frequency_converter.py
│   │   ├── audio_speed_converter.py
│   │   ├── audio_volume_converter.py
│   │   ├── audio_white_noise_converter.py
│   │   ├── azure_speech_audio_to_text_converter.py
│   │   ├── azure_speech_text_to_audio_converter.py
│   │   ├── base2048_converter.py
│   │   ├── base64_converter.py
│   │   ├── bin_ascii_converter.py
│   │   ├── binary_converter.py
│   │   ├── braille_converter.py
│   │   ├── caesar_converter.py
│   │   ├── character_space_converter.py
│   │   ├── charswap_attack_converter.py
│   │   ├── codechameleon_converter.py
│   │   ├── colloquial_wordswap_converter.py
│   │   ├── denylist_converter.py
│   │   ├── diacritic_converter.py
│   │   ├── ecoji_converter.py
│   │   ├── emoji_converter.py
│   │   ├── first_letter_converter.py
│   │   ├── flip_converter.py
│   │   ├── human_in_the_loop_converter.py
│   │   ├── image_compression_converter.py
│   │   ├── insert_punctuation_converter.py
│   │   ├── json_string_converter.py
│   │   ├── leetspeak_converter.py
│   │   ├── llm_generic_text_converter.py
│   │   ├── malicious_question_generator_converter.py
│   │   ├── math_obfuscation_converter.py
│   │   ├── math_prompt_converter.py
│   │   ├── morse_converter.py
│   │   ├── nato_converter.py
│   │   ├── negation_trap_converter.py
│   │   ├── noise_converter.py
│   │   ├── pdf_converter.py
│   │   ├── persuasion_converter.py
│   │   ├── prompt_converter.py
│   │   ├── qr_code_converter.py
│   │   ├── random_capital_letters_converter.py
│   │   ├── random_translation_converter.py
│   │   ├── repeat_token_converter.py
│   │   ├── rot13_converter.py
│   │   ├── scientific_translation_converter.py
│   │   ├── search_replace_converter.py
│   │   ├── selective_text_converter.py
│   │   ├── string_join_converter.py
│   │   ├── suffix_append_converter.py
│   │   ├── superscript_converter.py
│   │   ├── template_segment_converter.py
│   │   ├── tense_converter.py
│   │   ├── text_jailbreak_converter.py
│   │   ├── text_selection_strategy.py
│   │   ├── tone_converter.py
│   │   ├── toxic_sentence_generator_converter.py
│   │   ├── translation_converter.py
│   │   ├── transparency_attack_converter.py
│   │   ├── unicode_confusable_converter.py
│   │   ├── unicode_replacement_converter.py
│   │   ├── unicode_sub_converter.py
│   │   ├── url_converter.py
│   │   ├── variation_converter.py
│   │   ├── word_doc_converter.py
│   │   ├── word_level_converter.py
│   │   ├── zalgo_converter.py
│   │   └── zero_width_converter.py
│   ├── prompt_normalizer
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── normalizer_request.cpython-310.pyc
│   │   │   ├── prompt_converter_configuration.cpython-310.pyc
│   │   │   └── prompt_normalizer.cpython-310.pyc
│   │   ├── __init__.py
│   │   ├── normalizer_request.py
│   │   ├── prompt_converter_configuration.py
│   │   └── prompt_normalizer.py
│   ├── prompt_target
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── azure_blob_storage_target.cpython-310.pyc
│   │   │   ├── azure_ml_chat_target.cpython-310.pyc
│   │   │   ├── batch_helper.cpython-310.pyc
│   │   │   ├── crucible_target.cpython-310.pyc
│   │   │   ├── gandalf_target.cpython-310.pyc
│   │   │   ├── playwright_copilot_target.cpython-310.pyc
│   │   │   ├── playwright_target.cpython-310.pyc
│   │   │   ├── prompt_shield_target.cpython-310.pyc
│   │   │   ├── text_target.cpython-310.pyc
│   │   │   └── websocket_copilot_target.cpython-310.pyc
│   │   ├── common
│   │   │   ├── __pycache__
│   │   │   │   ├── prompt_chat_target.cpython-310.pyc
│   │   │   │   ├── prompt_target.cpython-310.pyc
│   │   │   │   ├── target_capabilities.cpython-310.pyc
│   │   │   │   └── utils.cpython-310.pyc
│   │   │   ├── prompt_chat_target.py
│   │   │   ├── prompt_target.py
│   │   │   ├── target_capabilities.py
│   │   │   └── utils.py
│   │   ├── http_target
│   │   │   ├── __pycache__
│   │   │   │   ├── http_target.cpython-310.pyc
│   │   │   │   ├── http_target_callback_functions.cpython-310.pyc
│   │   │   │   └── httpx_api_target.cpython-310.pyc
│   │   │   ├── http_target.py
│   │   │   ├── http_target_callback_functions.py
│   │   │   └── httpx_api_target.py
│   │   ├── hugging_face
│   │   │   ├── __pycache__
│   │   │   │   ├── hugging_face_chat_target.cpython-310.pyc
│   │   │   │   └── hugging_face_endpoint_target.cpython-310.pyc
│   │   │   ├── hugging_face_chat_target.py
│   │   │   └── hugging_face_endpoint_target.py
│   │   ├── openai
│   │   │   ├── __pycache__
│   │   │   │   ├── openai_chat_audio_config.cpython-310.pyc
│   │   │   │   ├── openai_chat_target.cpython-310.pyc
│   │   │   │   ├── openai_completion_target.cpython-310.pyc
│   │   │   │   ├── openai_error_handling.cpython-310.pyc
│   │   │   │   ├── openai_image_target.cpython-310.pyc
│   │   │   │   ├── openai_realtime_target.cpython-310.pyc
│   │   │   │   ├── openai_response_target.cpython-310.pyc
│   │   │   │   ├── openai_target.cpython-310.pyc
│   │   │   │   ├── openai_tts_target.cpython-310.pyc
│   │   │   │   └── openai_video_target.cpython-310.pyc
│   │   │   ├── openai_chat_audio_config.py
│   │   │   ├── openai_chat_target.py
│   │   │   ├── openai_completion_target.py
│   │   │   ├── openai_error_handling.py
│   │   │   ├── openai_image_target.py
│   │   │   ├── openai_realtime_target.py
│   │   │   ├── openai_response_target.py
│   │   │   ├── openai_target.py
│   │   │   ├── openai_tts_target.py
│   │   │   └── openai_video_target.py
│   │   ├── __init__.py
│   │   ├── azure_blob_storage_target.py
│   │   ├── azure_ml_chat_target.py
│   │   ├── batch_helper.py
│   │   ├── crucible_target.py
│   │   ├── gandalf_target.py
│   │   ├── playwright_copilot_target.py
│   │   ├── playwright_target.py
│   │   ├── prompt_shield_target.py
│   │   ├── rpc_client.py
│   │   ├── text_target.py
│   │   └── websocket_copilot_target.py
│   ├── registry
│   │   ├── class_registries
│   │   │   ├── __init__.py
│   │   │   ├── base_class_registry.py
│   │   │   ├── initializer_registry.py
│   │   │   └── scenario_registry.py
│   │   ├── instance_registries
│   │   │   ├── __init__.py
│   │   │   ├── base_instance_registry.py
│   │   │   ├── converter_registry.py
│   │   │   ├── scorer_registry.py
│   │   │   └── target_registry.py
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── discovery.py
│   ├── scenario
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   ├── atomic_attack.py
│   │   │   ├── dataset_configuration.py
│   │   │   ├── scenario.py
│   │   │   └── scenario_strategy.py
│   │   ├── printer
│   │   │   ├── __init__.py
│   │   │   ├── console_printer.py
│   │   │   └── scenario_result_printer.py
│   │   ├── scenarios
│   │   │   ├── airt
│   │   │   │   ├── __init__.py
│   │   │   │   ├── content_harms.py
│   │   │   │   ├── cyber.py
│   │   │   │   ├── jailbreak.py
│   │   │   │   ├── leakage.py
│   │   │   │   ├── psychosocial.py
│   │   │   │   └── scam.py
│   │   │   ├── foundry
│   │   │   │   ├── __init__.py
│   │   │   │   └── red_team_agent.py
│   │   │   ├── garak
│   │   │   │   ├── __init__.py
│   │   │   │   └── encoding.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── score
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── audio_transcript_scorer.cpython-310.pyc
│   │   │   ├── batch_scorer.cpython-310.pyc
│   │   │   ├── conversation_scorer.cpython-310.pyc
│   │   │   ├── score_aggregator_result.cpython-310.pyc
│   │   │   ├── score_utils.cpython-310.pyc
│   │   │   ├── scorer.cpython-310.pyc
│   │   │   ├── scorer_prompt_validator.cpython-310.pyc
│   │   │   └── video_scorer.cpython-310.pyc
│   │   ├── float_scale
│   │   │   ├── __pycache__
│   │   │   │   ├── audio_float_scale_scorer.cpython-310.pyc
│   │   │   │   ├── azure_content_filter_scorer.cpython-310.pyc
│   │   │   │   ├── float_scale_score_aggregator.cpython-310.pyc
│   │   │   │   ├── float_scale_scorer.cpython-310.pyc
│   │   │   │   ├── insecure_code_scorer.cpython-310.pyc
│   │   │   │   ├── plagiarism_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_general_float_scale_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_likert_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_scale_scorer.cpython-310.pyc
│   │   │   │   └── video_float_scale_scorer.cpython-310.pyc
│   │   │   ├── audio_float_scale_scorer.py
│   │   │   ├── azure_content_filter_scorer.py
│   │   │   ├── float_scale_score_aggregator.py
│   │   │   ├── float_scale_scorer.py
│   │   │   ├── insecure_code_scorer.py
│   │   │   ├── plagiarism_scorer.py
│   │   │   ├── self_ask_general_float_scale_scorer.py
│   │   │   ├── self_ask_likert_scorer.py
│   │   │   ├── self_ask_scale_scorer.py
│   │   │   └── video_float_scale_scorer.py
│   │   ├── human
│   │   │   ├── __pycache__
│   │   │   │   └── human_in_the_loop_gradio.cpython-310.pyc
│   │   │   └── human_in_the_loop_gradio.py
│   │   ├── printer
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   ├── console_scorer_printer.cpython-310.pyc
│   │   │   │   └── scorer_printer.cpython-310.pyc
│   │   │   ├── __init__.py
│   │   │   ├── console_scorer_printer.py
│   │   │   └── scorer_printer.py
│   │   ├── scorer_evaluation
│   │   │   ├── __pycache__
│   │   │   │   ├── human_labeled_dataset.cpython-310.pyc
│   │   │   │   ├── krippendorff.cpython-310.pyc
│   │   │   │   ├── metrics_type.cpython-310.pyc
│   │   │   │   ├── scorer_evaluator.cpython-310.pyc
│   │   │   │   ├── scorer_metrics.cpython-310.pyc
│   │   │   │   └── scorer_metrics_io.cpython-310.pyc
│   │   │   ├── human_labeled_dataset.py
│   │   │   ├── krippendorff.py
│   │   │   ├── metrics_type.py
│   │   │   ├── scorer_evaluation_identity.py
│   │   │   ├── scorer_evaluator.py
│   │   │   ├── scorer_metrics.py
│   │   │   └── scorer_metrics_io.py
│   │   ├── true_false
│   │   │   ├── __pycache__
│   │   │   │   ├── audio_true_false_scorer.cpython-310.pyc
│   │   │   │   ├── decoding_scorer.cpython-310.pyc
│   │   │   │   ├── float_scale_threshold_scorer.cpython-310.pyc
│   │   │   │   ├── gandalf_scorer.cpython-310.pyc
│   │   │   │   ├── markdown_injection.cpython-310.pyc
│   │   │   │   ├── prompt_shield_scorer.cpython-310.pyc
│   │   │   │   ├── question_answer_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_category_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_general_true_false_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_question_answer_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_refusal_scorer.cpython-310.pyc
│   │   │   │   ├── self_ask_true_false_scorer.cpython-310.pyc
│   │   │   │   ├── substring_scorer.cpython-310.pyc
│   │   │   │   ├── true_false_composite_scorer.cpython-310.pyc
│   │   │   │   ├── true_false_inverter_scorer.cpython-310.pyc
│   │   │   │   ├── true_false_score_aggregator.cpython-310.pyc
│   │   │   │   ├── true_false_scorer.cpython-310.pyc
│   │   │   │   └── video_true_false_scorer.cpython-310.pyc
│   │   │   ├── audio_true_false_scorer.py
│   │   │   ├── decoding_scorer.py
│   │   │   ├── float_scale_threshold_scorer.py
│   │   │   ├── gandalf_scorer.py
│   │   │   ├── markdown_injection.py
│   │   │   ├── prompt_shield_scorer.py
│   │   │   ├── question_answer_scorer.py
│   │   │   ├── self_ask_category_scorer.py
│   │   │   ├── self_ask_general_true_false_scorer.py
│   │   │   ├── self_ask_question_answer_scorer.py
│   │   │   ├── self_ask_refusal_scorer.py
│   │   │   ├── self_ask_true_false_scorer.py
│   │   │   ├── substring_scorer.py
│   │   │   ├── true_false_composite_scorer.py
│   │   │   ├── true_false_inverter_scorer.py
│   │   │   ├── true_false_score_aggregator.py
│   │   │   ├── true_false_scorer.py
│   │   │   └── video_true_false_scorer.py
│   │   ├── __init__.py
│   │   ├── audio_transcript_scorer.py
│   │   ├── batch_scorer.py
│   │   ├── conversation_scorer.py
│   │   ├── score_aggregator_result.py
│   │   ├── score_utils.py
│   │   ├── scorer.py
│   │   ├── scorer_prompt_validator.py
│   │   └── video_scorer.py
│   ├── setup
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── configuration_loader.cpython-310.pyc
│   │   │   └── initialization.cpython-310.pyc
│   │   ├── initializers
│   │   │   ├── scenarios
│   │   │   │   ├── __init__.py
│   │   │   │   ├── load_default_datasets.py
│   │   │   │   ├── objective_list.py
│   │   │   │   └── openai_objective_target.py
│   │   │   ├── __init__.py
│   │   │   ├── airt.py
│   │   │   ├── airt_targets.py
│   │   │   ├── pyrit_initializer.py
│   │   │   └── simple.py
│   │   ├── __init__.py
│   │   ├── configuration_loader.py
│   │   └── initialization.py
│   ├── ui
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── connection_status.py
│   │   ├── rpc.py
│   │   ├── rpc_client.py
│   │   └── scorer.py
│   ├── __init__.py
│   ├── py.typed
│   └── show_versions.py
├── pyrit.egg-info
│   ├── dependency_links.txt
│   ├── entry_points.txt
│   ├── PKG-INFO
│   ├── requires.txt
│   ├── SOURCES.txt
│   └── top_level.txt
├── tests
│   ├── end_to_end
│   │   ├── __init__.py
│   │   └── test_scenarios.py
│   ├── integration
│   │   ├── ai_recruiter
│   │   │   └── test_ai_recruiter.py
│   │   ├── auxiliary_attacks
│   │   │   └── test_notebooks_auxiliary.py
│   │   ├── converter
│   │   │   ├── test_entra_auth_converters.py
│   │   │   ├── test_notebooks_converter.py
│   │   │   └── test_retry_timing_integration.py
│   │   ├── datasets
│   │   │   ├── test_notebooks_datasets.py
│   │   │   └── test_seed_dataset_provider_integration.py
│   │   ├── embeddings
│   │   │   └── test_openai_embedding.py
│   │   ├── executors
│   │   │   └── test_executor_notebooks.py
│   │   ├── memory
│   │   │   ├── test_azure_sql_memory_integration.py
│   │   │   └── test_notebooks_memory.py
│   │   ├── message_normalizer
│   │   │   ├── __init__.py
│   │   │   └── test_tokenizer_template_normalizer_integration.py
│   │   ├── score
│   │   │   ├── test_azure_content_filter_integration.py
│   │   │   ├── test_hitl_gradio_integration.py
│   │   │   └── test_scorer_notebooks.py
│   │   ├── targets
│   │   │   ├── test_entra_auth_targets.py
│   │   │   ├── test_notebooks_targets.py
│   │   │   ├── test_openai_chat_target_integration.py
│   │   │   ├── test_openai_responses_gpt5.py
│   │   │   ├── test_rate_limiting_integration.py
│   │   │   ├── test_target_filters.py
│   │   │   └── test_targets_and_secrets.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── mocks.py
│   │   └── test_notebooks_cookbooks.py
│   └── unit
│       ├── analytics
│       │   ├── __init__.py
│       │   ├── test_conversation_analytics.py
│       │   ├── test_result_analysis.py
│       │   └── test_text_matching.py
│       ├── auth
│       │   ├── __init__.py
│       │   ├── test_azure_auth.py
│       │   ├── test_azure_storage_auth.py
│       │   └── test_copilot_authenticator.py
│       ├── auxiliary_attacks
│       │   ├── gcg
│       │   │   ├── __init__.py
│       │   │   ├── test_attack_manager_helpers.py
│       │   │   ├── test_get_goals_and_targets.py
│       │   │   ├── test_log.py
│       │   │   └── test_multi_prompt_attack.py
│       │   └── __init__.py
│       ├── backend
│       │   ├── __init__.py
│       │   ├── test_api_routes.py
│       │   ├── test_attack_service.py
│       │   ├── test_common_models.py
│       │   ├── test_converter_service.py
│       │   ├── test_error_handlers.py
│       │   ├── test_main.py
│       │   ├── test_mappers.py
│       │   ├── test_media_route.py
│       │   └── test_target_service.py
│       ├── build_scripts
│       │   └── test_sanitize_notebook_paths.py
│       ├── cli
│       │   ├── __init__.py
│       │   ├── test_frontend_core.py
│       │   ├── test_pyrit_backend.py
│       │   ├── test_pyrit_scan.py
│       │   └── test_pyrit_shell.py
│       ├── common
│       │   ├── test_common_default.py
│       │   ├── test_common_net_utility.py
│       │   ├── test_convert_local_image_to_data_url.py
│       │   ├── test_helper_functions.py
│       │   ├── test_hf_model_downloads.py
│       │   └── test_pyrit_default_value.py
│       ├── converter
│       │   ├── test_add_image_text_converter.py
│       │   ├── test_add_image_video_converter.py
│       │   ├── test_add_text_image_converter.py
│       │   ├── test_ansi_attack_converter.py
│       │   ├── test_ask_to_decode_converter.py
│       │   ├── test_audio_echo_converter.py
│       │   ├── test_audio_frequency_converter.py
│       │   ├── test_audio_speed_converter.py
│       │   ├── test_audio_volume_converter.py
│       │   ├── test_audio_white_noise_converter.py
│       │   ├── test_azure_speech_converter.py
│       │   ├── test_azure_speech_text_converter.py
│       │   ├── test_base2048_converter.py
│       │   ├── test_bin_ascii_converter.py
│       │   ├── test_binary_converter.py
│       │   ├── test_braille_converter.py
│       │   ├── test_char_swap_generator_converter.py
│       │   ├── test_code_chameleon_converter.py
│       │   ├── test_colloquial_wordswap_converter.py
│       │   ├── test_denylist_converter.py
│       │   ├── test_diacritics_converter.py
│       │   ├── test_ecoji_converter.py
│       │   ├── test_first_letter_converter.py
│       │   ├── test_generic_llm_converter.py
│       │   ├── test_image_compression_converter.py
│       │   ├── test_insert_punctuation_converter.py
│       │   ├── test_json_string_converter.py
│       │   ├── test_leetspeak_converter.py
│       │   ├── test_math_obfuscation_converter.py
│       │   ├── test_math_prompt_converter.py
│       │   ├── test_nato_converter.py
│       │   ├── test_negation_trap_converter.py
│       │   ├── test_pdf_converter.py
│       │   ├── test_persuasion_converter.py
│       │   ├── test_prompt_converter.py
│       │   ├── test_qr_code_converter.py
│       │   ├── test_random_translation_converter.py
│       │   ├── test_repeat_token_converter.py
│       │   ├── test_scientific_translation_converter.py
│       │   ├── test_selective_text_converter.py
│       │   ├── test_superscript_converter.py
│       │   ├── test_template_segment_converter.py
│       │   ├── test_text_jailbreak_converter.py
│       │   ├── test_text_selection_strategy.py
│       │   ├── test_token_smuggler_converter.py
│       │   ├── test_toxic_sentence_generator_converter.py
│       │   ├── test_translation_converter.py
│       │   ├── test_transparency_attack_converter.py
│       │   ├── test_unicode_confusable_converter.py
│       │   ├── test_variation_converter.py
│       │   ├── test_word_doc_converter.py
│       │   ├── test_word_level_converter.py
│       │   ├── test_zalgo_converter.py
│       │   └── test_zero_width_converter.py
│       ├── data
│       │   ├── embedding_1.json
│       │   └── embedding_2.json
│       ├── datasets
│       │   ├── test_beaver_tails_dataset.py
│       │   ├── test_harmful_qa_dataset.py
│       │   ├── test_jailbreak_text.py
│       │   ├── test_local_dataset_loader.py
│       │   ├── test_or_bench_dataset.py
│       │   ├── test_promptintel_dataset.py
│       │   ├── test_remote_dataset_loader.py
│       │   ├── test_salad_bench_dataset.py
│       │   ├── test_seed_dataset_provider.py
│       │   ├── test_simple_safety_tests_dataset.py
│       │   ├── test_toxic_chat_dataset.py
│       │   ├── test_transphobia_awareness_dataset.py
│       │   └── test_vlsu_multimodal_dataset.py
│       ├── docs
│       │   ├── test_api_documentation.py
│       │   └── test_converter_documentation.py
│       ├── embedding
│       │   └── test_azure_text_embedding.py
│       ├── exceptions
│       │   ├── test_exception_context.py
│       │   ├── test_exceptions.py
│       │   └── test_exceptions_helpers.py
│       ├── executor
│       │   ├── attack
│       │   │   ├── component
│       │   │   │   ├── test_conversation_manager.py
│       │   │   │   └── test_simulated_conversation.py
│       │   │   ├── core
│       │   │   │   ├── test_attack_config.py
│       │   │   │   ├── test_attack_executor.py
│       │   │   │   ├── test_attack_parameters.py
│       │   │   │   ├── test_attack_strategy.py
│       │   │   │   └── test_markdown_printer.py
│       │   │   ├── multi_turn
│       │   │   │   ├── test_chunked_request.py
│       │   │   │   ├── test_crescendo.py
│       │   │   │   ├── test_multi_prompt_sending.py
│       │   │   │   ├── test_red_team_system.py
│       │   │   │   ├── test_red_teaming.py
│       │   │   │   ├── test_supports_multi_turn_attacks.py
│       │   │   │   └── test_tree_of_attacks.py
│       │   │   ├── single_turn
│       │   │   │   ├── test_context_compliance.py
│       │   │   │   ├── test_flip_attack.py
│       │   │   │   ├── test_many_shot_jailbreak.py
│       │   │   │   ├── test_many_shot_template.py
│       │   │   │   ├── test_prompt_sending.py
│       │   │   │   ├── test_role_play.py
│       │   │   │   └── test_skeleton_key.py
│       │   │   ├── test_attack_parameter_consistency.py
│       │   │   └── test_error_skip_scoring.py
│       │   ├── benchmark
│       │   │   ├── test_fairness_bias.py
│       │   │   └── test_question_answering.py
│       │   ├── core
│       │   │   └── test_strategy.py
│       │   ├── promptgen
│       │   │   ├── fuzzer
│       │   │   │   ├── test_fuzzer.py
│       │   │   │   └── test_fuzzer_converter.py
│       │   │   └── test_anecdoctor.py
│       │   └── workflow
│       │       └── test_xpia.py
│       ├── identifiers
│       │   ├── __init__.py
│       │   ├── test_component_identifier.py
│       │   └── test_evaluation_identity.py
│       ├── memory
│       │   ├── memory_interface
│       │   │   ├── conftest.py
│       │   │   ├── test_interface_attack_results.py
│       │   │   ├── test_interface_core.py
│       │   │   ├── test_interface_export.py
│       │   │   ├── test_interface_prompts.py
│       │   │   ├── test_interface_scenario_results.py
│       │   │   ├── test_interface_scores.py
│       │   │   └── test_interface_seed_prompts.py
│       │   ├── __init__.py
│       │   ├── test_azure_sql_memory.py
│       │   ├── test_central_memory.py
│       │   ├── test_memory_embedding.py
│       │   ├── test_memory_exporter.py
│       │   ├── test_score_entry.py
│       │   └── test_sqlite_memory.py
│       ├── message_normalizer
│       │   ├── test_chat_message_normalizer.py
│       │   ├── test_chat_normalizer_tokenizer.py
│       │   ├── test_conversation_context_normalizer.py
│       │   └── test_generic_system_squash_normalizer.py
│       ├── models
│       │   ├── test_data_type_serializer.py
│       │   ├── test_embedding_response.py
│       │   ├── test_harm_definition.py
│       │   ├── test_json_response_config.py
│       │   ├── test_literals.py
│       │   ├── test_message.py
│       │   ├── test_message_piece.py
│       │   ├── test_models.py
│       │   ├── test_score.py
│       │   ├── test_seed.py
│       │   ├── test_seed_attack_technique_group.py
│       │   ├── test_seed_group.py
│       │   ├── test_seed_simulated_conversation.py
│       │   └── test_storage_io.py
│       ├── prompt_normalizer
│       │   ├── test_normalizer_request.py
│       │   └── test_prompt_normalizer.py
│       ├── registry
│       │   ├── __init__.py
│       │   ├── test_base.py
│       │   ├── test_base_instance_registry.py
│       │   ├── test_converter_registry.py
│       │   ├── test_scorer_registry.py
│       │   └── test_target_registry.py
│       ├── scenarios
│       │   ├── test_atomic_attack.py
│       │   ├── test_content_harms.py
│       │   ├── test_cyber.py
│       │   ├── test_dataset_configuration.py
│       │   ├── test_encoding.py
│       │   ├── test_foundry.py
│       │   ├── test_jailbreak.py
│       │   ├── test_leakage_scenario.py
│       │   ├── test_psychosocial_harms.py
│       │   ├── test_scam.py
│       │   ├── test_scenario.py
│       │   ├── test_scenario_partial_results.py
│       │   ├── test_scenario_retry.py
│       │   └── test_strategy_validation.py
│       ├── score
│       │   ├── test_audio_scorer.py
│       │   ├── test_azure_content_filter.py
│       │   ├── test_batch_scorer.py
│       │   ├── test_conversation_history_scorer.py
│       │   ├── test_decoding_scorer.py
│       │   ├── test_float_scale_score_aggregator.py
│       │   ├── test_float_scale_threshold_scorer.py
│       │   ├── test_gandalf_scorer.py
│       │   ├── test_general_float_scale_scorer.py
│       │   ├── test_general_true_false_scorer.py
│       │   ├── test_hitl_gradio.py
│       │   ├── test_human_labeled_dataset.py
│       │   ├── test_insecure_code_scorer.py
│       │   ├── test_krippendorff.py
│       │   ├── test_markdown_injection.py
│       │   ├── test_plagiarism_scorer.py
│       │   ├── test_prompt_shield_scorer.py
│       │   ├── test_question_answer_scorer.py
│       │   ├── test_score_utils.py
│       │   ├── test_scorer.py
│       │   ├── test_scorer_eval_csv_schema.py
│       │   ├── test_scorer_evaluation_identity.py
│       │   ├── test_scorer_evaluator.py
│       │   ├── test_scorer_metrics.py
│       │   ├── test_scorer_prompt_validator.py
│       │   ├── test_self_ask_category.py
│       │   ├── test_self_ask_likert.py
│       │   ├── test_self_ask_refusal.py
│       │   ├── test_self_ask_scale.py
│       │   ├── test_self_ask_true_false.py
│       │   ├── test_substring.py
│       │   ├── test_true_false_composite_scorer.py
│       │   ├── test_true_false_inverter.py
│       │   ├── test_true_false_score_aggregator.py
│       │   └── test_video_scorer.py
│       ├── setup
│       │   ├── test_airt_initializer.py
│       │   ├── test_airt_targets_initializer.py
│       │   ├── test_configuration_loader.py
│       │   ├── test_initialization.py
│       │   ├── test_load_default_datasets.py
│       │   ├── test_pyrit_initializer.py
│       │   └── test_simple_initializer.py
│       ├── target
│       │   ├── test_azure_ml_chat_target.py
│       │   ├── test_azure_openai_completion_target.py
│       │   ├── test_chat_audio_config.py
│       │   ├── test_crucible_target.py
│       │   ├── test_gandalf_target.py
│       │   ├── test_http_api_target.py
│       │   ├── test_http_target.py
│       │   ├── test_http_target_parsing.py
│       │   ├── test_hugging_face_endpoint_target.py
│       │   ├── test_huggingface_chat_target.py
│       │   ├── test_image_target.py
│       │   ├── test_openai_chat_target.py
│       │   ├── test_openai_error_handling.py
│       │   ├── test_openai_response_target.py
│       │   ├── test_openai_response_target_function_chaining.py
│       │   ├── test_openai_target_auth.py
│       │   ├── test_openai_url_warnings.py
│       │   ├── test_playwright_copilot_target.py
│       │   ├── test_playwright_target.py
│       │   ├── test_prompt_shield_target.py
│       │   ├── test_prompt_target.py
│       │   ├── test_prompt_target_azure_blob_storage.py
│       │   ├── test_prompt_target_text.py
│       │   ├── test_realtime_target.py
│       │   ├── test_supports_multi_turn.py
│       │   ├── test_token_provider_wrapping.py
│       │   ├── test_tts_target.py
│       │   ├── test_video_target.py
│       │   └── test_websocket_copilot_target.py
│       ├── __init__.py
│       ├── conftest.py
│       └── mocks.py
├── CITATION.cff
├── CODE_OF_CONDUCT.md
├── component-governance.yml
├── end-to-end-tests.yml
├── integration-tests.yml
├── LICENSE
├── Makefile
├── MANIFEST.in
├── NOTICE.txt
├── policheck.yml
├── pyproject.toml
├── pyrightconfig.json
├── README.md
├── SECURITY.md
├── SUPPORT.md
├── UPDATE_LOG.md
└── uv.lock

[ 📁 271 directories, 📄 1791 files ]
```
