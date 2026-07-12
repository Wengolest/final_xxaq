function mcp_modeling_analysis()
% MCP 原生 Agent 投毒实验 — 数学建模与出图
% 读取 MCP_result 下最新 mcp_eval_native_full_*.csv

    % modeling/ -> MCP_test/ -> 项目根 lucky_xxaq/
    modelingDir = fileparts(mfilename('fullpath'));
    projectRoot = fileparts(fileparts(modelingDir));
    resultDir = fullfile(projectRoot, 'MCP_result');
    figDir = fullfile(resultDir, 'figures');
    if ~exist(figDir, 'dir')
        mkdir(figDir);
    end

  % 优先 native 实验 CSV，回退旧 unified CSV
    nativeFiles = dir(fullfile(resultDir, 'mcp_eval_native_full_*.csv'));
    legacyFiles = dir(fullfile(resultDir, 'mcp_eval_full_*.csv'));
    if ~isempty(nativeFiles)
        csvFiles = nativeFiles;
    else
        csvFiles = legacyFiles;
    end
    if isempty(csvFiles)
        error('No mcp_eval_native_full_*.csv or mcp_eval_full_*.csv in MCP_result');
    end
    [~, idx] = max([csvFiles.datenum]);
    csvPath = fullfile(resultDir, csvFiles(idx).name);
    fprintf('Using CSV: %s\n', csvPath);

    T = readtable(csvPath, 'TextType', 'string', 'VariableNamingRule', 'preserve');
    T = rename_native_csv_columns(T);
    T = coerce_native_csv_types(T);

    % --- Layer 1: ASR with Wilson CI ---
    agents = unique(T.agent_framework);
    nAgents = numel(agents);
    asr = zeros(nAgents, 1);
    ciLo = zeros(nAgents, 1);
    ciHi = zeros(nAgents, 1);
    for i = 1:nAgents
        sub = T(T.agent_framework == agents(i), :);
        k = sum(sub.attack_success == true | sub.attack_success == 1);
        n = height(sub);
        [asr(i), ciLo(i), ciHi(i)] = wilson_ci(k, n);
    end

    fig1 = figure('Visible', 'off', 'Position', [100 100 900 500]);
    bar(asr, 'FaceColor', [0.85 0.33 0.1]);
    hold on;
    errorbar(1:nAgents, asr, asr - ciLo, ciHi - asr, 'k.', 'LineWidth', 1.2);
    set(gca, 'XTick', 1:nAgents, 'XTickLabel', agents, 'XTickLabelRotation', 30);
    ylabel('ASR (Attack Success Rate)');
    title('Layer 1: Native Agent ASR with 95% Wilson CI');
    grid on;
    saveas(fig1, fullfile(figDir, 'fig1_asr_by_agent.png'));
    close(fig1);

    % --- Layer 1: Paradigm heatmap ---
    paradigms = unique(T.attack_paradigm);
    heat = zeros(nAgents, numel(paradigms));
    for i = 1:nAgents
        for j = 1:numel(paradigms)
            sub = T(T.agent_framework == agents(i) & T.attack_paradigm == paradigms(j), :);
            if height(sub) > 0
                heat(i, j) = mean(sub.attack_success == true | sub.attack_success == 1);
            end
        end
    end

    fig2 = figure('Visible', 'off', 'Position', [100 100 800 500]);
    imagesc(heat);
    colorbar;
    colormap(hot);
    caxis([0 1]);
    set(gca, 'XTick', 1:numel(paradigms), 'XTickLabel', paradigms);
    set(gca, 'YTick', 1:nAgents, 'YTickLabel', agents);
    xlabel('Paradigm'); ylabel('Agent');
    title('Layer 1: ASR Heatmap (Agent x Paradigm)');
    saveas(fig2, fullfile(figDir, 'fig2_heatmap_agent_paradigm.png'));
    close(fig2);

    % --- Layer 2: Markov chain transition rates ---
    s0 = sum(T.chain_s0); s1 = sum(T.chain_s1); s2 = sum(T.chain_s2);
    s3 = sum(T.chain_s3); s4 = sum(T.chain_s4);
    p1 = s1 / max(s0, 1);
    p2 = s2 / max(s1, 1);
    p3 = s3 / max(s2, 1);
    p4 = s4 / max(s3, 1);
    probs = [p1 p2 p3 p4];
    labels = {'S0→S1', 'S1→S2', 'S2→S3', 'S3→S4'};

    fig3 = figure('Visible', 'off');
    bar(probs, 'FaceColor', [0.2 0.6 0.8]);
    set(gca, 'XTickLabel', labels, 'XTickLabelRotation', 20);
    ylabel('Transition probability');
    title('Layer 2: Attack Chain Markov Transitions');
    ylim([0 1]);
    grid on;
    saveas(fig3, fullfile(figDir, 'fig3_markov_transitions.png'));
    close(fig3);

    % --- Layer 3: H = ASR * (1-DSR) * I ---
    if ismember('impact_weight', T.Properties.VariableNames)
        Imean = mean(T.impact_weight);
    else
        Imean = 3.5;
    end
    rawRows = T;
    if ismember('mode', T.Properties.VariableNames)
        rawRows = T(T.mode == "raw", :);
    end
    asrOverall = mean(rawRows.attack_success == true | rawRows.attack_success == 1);
    if ismember('mode', T.Properties.VariableNames) && any(T.mode == "sanitized")
        san = T(T.mode == "sanitized", :);
        dsr = 1 - mean(san.attack_success == true | san.attack_success == 1);
    else
        dsr = 0.5;
    end
    H = asrOverall * (1 - dsr) * Imean;

    fig4 = figure('Visible', 'off');
    bar([asrOverall, dsr, H], 'FaceColor', [0.4 0.7 0.4]);
    set(gca, 'XTickLabel', {'ASR', '1-DSR', 'H score'});
    title(sprintf('Layer 3: Unified H = ASR*(1-DSR)*I, I=%.2f', Imean));
    grid on;
    saveas(fig4, fullfile(figDir, 'fig4_h_score.png'));
    close(fig4);

    outTxt = fullfile(resultDir, 'modeling_summary.txt');
    fid = fopen(outTxt, 'w');
    fprintf(fid, 'MCP Native Modeling Summary\n');
    fprintf(fid, 'CSV: %s\n', csvPath);
    fprintf(fid, 'Overall ASR: %.4f\n', asrOverall);
    fprintf(fid, 'DSR (independent): %.4f\n', dsr);
    fprintf(fid, 'Mean impact I: %.4f\n', Imean);
    fprintf(fid, 'H score: %.4f\n', H);
    fprintf(fid, 'Markov: p1=%.4f p2=%.4f p3=%.4f p4=%.4f\n', p1, p2, p3, p4);
    for i = 1:nAgents
        fprintf(fid, 'Agent %s ASR=%.4f CI=[%.4f,%.4f]\n', agents(i), asr(i), ciLo(i), ciHi(i));
    end
    fclose(fid);
    fprintf('Modeling complete. Figures in %s\n', figDir);
end

function T = rename_native_csv_columns(T)
% 双语表头 CSV -> 脚本内英文列名
    pairs = {
        'Run batch ID (运行批次ID)', 'run_id'
        'Experiment mode (实验模式)', 'mode'
        'Agent framework (Agent框架)', 'agent_framework'
        'Attack paradigm (攻击范式)', 'attack_paradigm'
        'Attack success (攻击是否成功)', 'attack_success'
        'Impact weight I(c) (影响权重)', 'impact_weight'
        'Chain S0 user task (链S0用户任务)', 'chain_s0'
        'Chain S1 tool selected (链S1工具选择)', 'chain_s1'
        'Chain S2 pre-step (链S2前置步骤)', 'chain_s2'
        'Chain S3 trigger tool (链S3触发工具)', 'chain_s3'
        'Chain S4 harm achieved (链S4危害达成)', 'chain_s4'
    };
    for i = 1:size(pairs, 1)
        oldName = pairs{i, 1};
        newName = pairs{i, 2};
        if ismember(oldName, T.Properties.VariableNames)
            T = renamevars(T, oldName, newName);
        end
    end
end

function T = coerce_native_csv_types(T)
    boolCols = {'attack_success'};
    numCols = {'chain_s0','chain_s1','chain_s2','chain_s3','chain_s4','impact_weight'};
    for c = boolCols
        if ismember(c{1}, T.Properties.VariableNames)
            v = lower(strtrim(string(T.(c{1}))));
            T.(c{1}) = (v == "true") | (v == "1");
        end
    end
    for c = numCols
        if ismember(c{1}, T.Properties.VariableNames)
            T.(c{1}) = str2double(string(T.(c{1})));
        end
    end
end

function [p, lo, hi] = wilson_ci(k, n, z)
    if nargin < 3, z = 1.96; end
    if n == 0
        p = 0; lo = 0; hi = 0; return;
    end
    phat = k / n;
    denom = 1 + z^2 / n;
    center = (phat + z^2 / (2*n)) / denom;
    margin = z * sqrt((phat*(1-phat) + z^2/(4*n)) / n) / denom;
    p = phat;
    lo = max(0, center - margin);
    hi = min(1, center + margin);
end
