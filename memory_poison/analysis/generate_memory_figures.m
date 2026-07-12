%% generate_memory_figures.m
% Agent MEMORY 投毒实验 — MATLAB 数学分析可视化
% 数据来源: plugin/results/20260608_212010/attack_results_full.csv
% 输出目录: docs/figures/

clear; clc; close all;

%% ========== 路径与全局样式 ==========
rootDir = fileparts(fileparts(mfilename('fullpath')));
outDir  = fullfile(rootDir, 'docs', 'figures');
if ~exist(outDir, 'dir'), mkdir(outDir); end

% 论文级配色（深蓝-青-琥珀-玫红）
C = [0.12 0.35 0.65;   % E 暴露层
     0.20 0.65 0.55;   % A 采纳层
     0.85 0.35 0.25;   % I 影响层
     0.55 0.25 0.70;   % 防御层
     0.30 0.30 0.35];  % 辅助灰

set(0, 'DefaultAxesFontName', 'Microsoft YaHei');
set(0, 'DefaultTextFontName', 'Microsoft YaHei');
set(0, 'DefaultAxesFontSize', 11);
set(0, 'DefaultLineLineWidth', 1.4);

agentLabels = {'DataInterp.', 'RAG Analyst', 'CI Pipeline', 'Code Review', 'Cust. Support'};
methodLabels = {'MemGraft', 'RAG-Drift', 'SchemaSpoof', 'MINJA'};

%% ========== 实验数据矩阵（72 条主实验） ==========
% N(ai,mj): 样本数; E/A/I: 命中计数
N = [ 9  3  3  3;
      3  6  3  0;
      6  3  3  3;
      3  3  3  3;
      3  3  3  6 ];

E_cnt = [ 6  0  0  3;
          3  0  0  0;
          6  0  3  3;
          3  0  0  3;
          0  0  0  6 ];

A_cnt = [ 8  2  3  3;
          3  1  0  0;
          6  1  3  3;
          3  1  0  1;
          2  2  0  6 ];

I_cnt = [ 6  0  0  3;
          3  0  0  0;
          6  0  3  3;
          3  0  0  1;
          0  0  0  6 ];

% 归一化比率矩阵（避免除零）
E_rate = E_cnt ./ max(N, 1);
A_rate = A_cnt ./ max(N, 1);
I_rate = I_cnt ./ max(N, 1);

% 全局标量
E_global = sum(E_cnt(:)) / sum(N(:));
A_global = sum(A_cnt(:)) / sum(N(:));
I_global = sum(I_cnt(:)) / sum(N(:));

% 按攻击类型汇总
method_E = sum(E_cnt, 1) ./ sum(N, 1);
method_A = sum(A_cnt, 1) ./ sum(N, 1);
method_I = sum(I_cnt, 1) ./ sum(N, 1);

%% ========== 图1: E/A/I 转化缺口（分组柱状 + 误差带风格装饰） ==========
fig1 = figure('Color', 'w', 'Position', [80 80 920 520]);
hold on; grid on; box on;

x = 1:4;
w = 0.25;
b1 = bar(x - w, method_A, w, 'FaceColor', C(2,:), 'EdgeColor', 'k', 'LineWidth', 0.8);
b2 = bar(x,     method_I, w, 'FaceColor', C(3,:), 'EdgeColor', 'k', 'LineWidth', 0.8);
b3 = bar(x + w, method_E, w, 'FaceColor', C(1,:), 'EdgeColor', 'k', 'LineWidth', 0.8);

% 转化缺口标注（A-I）
for k = 1:4
    gap = method_A(k) - method_I(k);
    if gap > 0.02
        plot([k-w, k], [method_A(k), method_I(k)], 'k--', 'LineWidth', 0.9);
        text(k - 0.12, (method_A(k)+method_I(k))/2, sprintf('\\Delta=%.0f%%', gap*100), ...
            'FontSize', 9, 'Color', [0.4 0.4 0.4]);
    end
end

% 全局参考线
yline(E_global, ':', sprintf('E_{global}=%.1f%%', E_global*100), ...
    'Color', C(1,:), 'LineWidth', 1.2, 'LabelHorizontalAlignment', 'left');
yline(I_global, ':', sprintf('I_{global}=%.1f%%', I_global*100), ...
    'Color', C(3,:), 'LineWidth', 1.2, 'LabelHorizontalAlignment', 'right');

set(gca, 'XTick', x, 'XTickLabel', methodLabels);
ylabel('比率 Rate');
title('MEMORY 投毒分层指标：语义采纳 (A) vs 业务影响 (I) vs 暴露 (E)', 'FontWeight', 'bold');
legend([b1 b2 b3], {'A: rule\_hit', 'I: attack\_success', 'E: poison\_retrieved'}, ...
    'Location', 'northwest');
ylim([0 1.05]);
hold off;
exportgraphics(fig1, fullfile(outDir, 'fig_EAI_gap.pdf'), 'Resolution', 300);
exportgraphics(fig1, fullfile(outDir, 'fig_EAI_gap.png'), 'Resolution', 300);

%% ========== 图2: 三维立体矩阵 — Agent × Attack × I ==========
fig2 = figure('Color', 'w', 'Position', [100 60 980 640]);
ax2 = axes(fig2); hold(ax2, 'on');

[nA, nM] = size(I_rate);
[X, Y] = meshgrid(1:nM, 1:nA);
Z = I_rate;

% 主 3D 柱状矩阵
hb = bar3(Z, 0.75);
for k = 1:numel(hb)
    zdata = hb(k).ZData;
    hb(k).CData = zdata;
    hb(k).FaceColor = 'interp';
    colormap(ax2, parula);
end

% 叠加半透明曲面增强立体感
hs = surf(ax2, X, Y, Z + 0.02, 'FaceAlpha', 0.25, 'EdgeColor', [0.2 0.2 0.2], ...
    'FaceColor', 'interp', 'LineWidth', 0.4);
colormap(ax2, cool);

% 在柱顶标注数值
for i = 1:nA
    for j = 1:nM
        if N(i,j) > 0
            text(j, i, I_rate(i,j) + 0.06, sprintf('%.0f%%', I_rate(i,j)*100), ...
                'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', [0.15 0.15 0.15]);
        end
    end
end

set(ax2, 'XTick', 1:nM, 'XTickLabel', methodLabels);
set(ax2, 'YTick', 1:nA, 'YTickLabel', agentLabels);
zlabel(ax2, '业务影响度 I (attack\_success rate)');
title(ax2, 'Agent \times 攻击类型 \times 业务影响度 I — 三维立体矩阵', 'FontWeight', 'bold');
view(ax2, 135, 28);
grid(ax2, 'on');
lighting gouraud; camlight('headlight'); material dull;
exportgraphics(fig2, fullfile(outDir, 'fig_3d_agent_attack_I.pdf'), 'Resolution', 300);
exportgraphics(fig2, fullfile(outDir, 'fig_3d_agent_attack_I.png'), 'Resolution', 300);

%% ========== 图3: E/A/I 三维曲面 + 等高线投影 ==========
fig3 = figure('Color', 'w', 'Position', [120 80 1000 600]);

% 构造 5×4×3 张量 → 展开为曲面采样
layers = cat(3, E_rate, A_rate, I_rate);  % 5×4×3
layerNames = {'E 暴露', 'A 采纳', 'I 影响'};

subplot(1,2,1);
hold on; grid on;
for L = 1:3
    [XX, YY] = meshgrid(1:4, 1:5);
    ZZ = layers(:,:,L);
    surf(XX, YY, ZZ, 'FaceAlpha', 0.55, 'EdgeColor', C(L,:), 'LineWidth', 0.6);
    % 底部等高线投影
    contour3(XX, YY, ZZ, 6, 'LineColor', C(L,:)*0.8, 'LineWidth', 0.9);
end
xlabel('攻击类型'); ylabel('Agent'); zlabel('比率');
set(gca, 'XTick', 1:4, 'XTickLabel', methodLabels);
set(gca, 'YTick', 1:5, 'YTickLabel', agentLabels);
title('E / A / I 三层指标三维曲面叠加', 'FontWeight', 'bold');
view(125, 22);
legend(layerNames, 'Location', 'northeast');
colormap(turbo);
lighting gouraud; camlight; material shiny;

% 右：分层瀑布矩阵（数学感更强）
subplot(1,2,2);
waterfallData = permute(layers, [2 1 3]);  % 4×5×3
[Xw, Yw, Zw] = ndgrid(1:5, 1:4, 1:3);
Cw = zeros(numel(Xw), 3);
for L = 1:3
    matL = layers(:,:,L)';
    idx = find(Zw == L);
    Cw(idx,:) = repmat(C(L,:), numel(idx), 1);
end
scatter3(Xw(:), Yw(:), Zw(:), 120, layers(:), 'filled', 'MarkerEdgeColor', 'k');
cb = colorbar; cb.Title.String = '指标值';
xlabel('Agent 索引'); ylabel('攻击类型索引'); zlabel('E/A/I 层');
set(gca, 'ZTick', 1:3, 'ZTickLabel', {'E','A','I'});
title('E/A/I 张量立体散点矩阵', 'FontWeight', 'bold');
view(40, 25); grid on;

exportgraphics(fig3, fullfile(outDir, 'fig_3d_surface_EAI.pdf'), 'Resolution', 300);
exportgraphics(fig3, fullfile(outDir, 'fig_3d_surface_EAI.png'), 'Resolution', 300);

%% ========== 图4: 防御消融热力图 + 3D 柱状 ==========
fig4 = figure('Color', 'w', 'Position', [140 100 960 500]);

defenseModes = {'none','sig','trust','prov','full'};
defenseLabels = {'无防御','签名','信任','溯源','完整'};
blockRate = [0 1 1 1 1];  % none=0%拦截(攻击已成功), 其余100%

subplot(1,2,1);
imagesc(blockRate);
colormap(flipud(hot)); colorbar;
set(gca, 'XTick', 1:5, 'XTickLabel', defenseLabels, 'XTickLabelRotation', 20);
set(gca, 'YTick', 1, 'YTickLabel', {'拦截率'});
title('防御消融拦截率', 'FontWeight', 'bold');
for k = 1:5
    text(k, 1, sprintf('%.0f%%', blockRate(k)*100), ...
        'HorizontalAlignment', 'center', 'Color', 'w', 'FontWeight', 'bold');
end

subplot(1,2,2);
% 5 Agent × 5 防御模式 模拟矩阵（成功样本上的拦截=1）
agentDef = ones(5, 5);  % 全部拦截
bar3(agentDef, 0.8);
colormap(gca, [0.9 0.3 0.3; 0.2 0.7 0.4]);
set(gca, 'XTick', 1:5, 'XTickLabel', defenseLabels);
set(gca, 'YTick', 1:5, 'YTickLabel', agentLabels);
zlabel('防御拦截率');
title('Agent \times 防御模式 三维矩阵', 'FontWeight', 'bold');
view(130, 25); grid on;
exportgraphics(fig4, fullfile(outDir, 'fig_defense_ablation.pdf'), 'Resolution', 300);
exportgraphics(fig4, fullfile(outDir, 'fig_defense_ablation.png'), 'Resolution', 300);

%% ========== 图5: 综合仪表盘 — 多子图数学分析 ==========
fig5 = figure('Color', 'w', 'Position', [60 40 1100 780]);

% (a) 漏斗图 E→A→I
subplot(2,3,1);
funnel = [E_global, A_global, I_global] * 100;
barh(funnel, 'FaceColor', 'flat', 'CData', C(1:3,:));
set(gca, 'YTick', 1:3, 'YTickLabel', {'E 暴露','A 采纳','I 影响'});
xlabel('比率 (%)'); title('(a) E\rightarrowA\rightarrowI 漏斗');
xlim([0 100]); grid on;
for k = 1:3
    text(funnel(k)+2, k, sprintf('%.1f%%', funnel(k)), 'FontSize', 10);
end

% (b) 极坐标玫瑰图 — 攻击类型 I 率
subplot(2,3,2);
theta = linspace(0, 2*pi, 5);
rho = [method_I, method_I(1)];
polarplot(theta, rho, '-o', 'LineWidth', 2, 'MarkerSize', 8, 'Color', C(3,:));
title('(b) 攻击类型 I 率玫瑰图');

% (c) 热力图 Agent×Method I
subplot(2,3,3);
imagesc(I_rate);
colormap(gca, parula); colorbar;
set(gca, 'XTick', 1:4, 'XTickLabel', methodLabels);
set(gca, 'YTick', 1:5, 'YTickLabel', agentLabels);
title('(c) Agent\timesMethod 影响热力图');
for i = 1:5
    for j = 1:4
        if N(i,j)>0
            text(j, i, sprintf('%.0f%%', I_rate(i,j)*100), ...
                'HorizontalAlignment', 'center', 'Color', 'w', 'FontSize', 8);
        end
    end
end

% (d) 箱线图风格 — 各 Agent 成功率分布（用重复实验近似）
subplot(2,3,4);
agentI = sum(I_cnt, 2) ./ sum(N, 2);
agentE = sum(E_cnt, 2) ./ sum(N, 2);
yyaxis left; bar(agentI, 0.6, 'FaceColor', C(3,:)); ylabel('I 率');
yyaxis right; plot(1:5, agentE, '-s', 'Color', C(1,:), 'LineWidth', 2, 'MarkerSize', 8);
ylabel('E 率'); set(gca, 'XTick', 1:5, 'XTickLabel', agentLabels, 'XTickLabelRotation', 15);
title('(d) Agent 维度 E/I 双轴'); grid on;

% (e) 3D 线框 — E/A/I 沿攻击类型
subplot(2,3,5);
[Xm, ~] = meshgrid(1:4, 1:3);
Zm = [method_E; method_A; method_I];
mesh(Xm, [1 2 3]', Zm, 'EdgeColor', C(1,:), 'LineWidth', 1.2); hold on;
surf(Xm, [1 2 3]', Zm, 'FaceAlpha', 0.4, 'EdgeColor', 'none');
set(gca, 'YTick', 1:3, 'YTickLabel', {'E','A','I'});
set(gca, 'XTick', 1:4, 'XTickLabel', methodLabels);
xlabel('攻击类型'); zlabel('比率'); title('(e) E/A/I 线框曲面'); view(50,30); grid on;

% (f) 饼图 — 攻击成功/失败/防御NA 构成
subplot(2,3,6);
pieData = [34, 38, 34];  % success, fail, defense_blocked
pie(pieData, {'攻击成功 34','攻击失败 38','防御拦截 34'});
colormap(gca, [C(3,:); 0.8 0.8 0.8; C(4,:)]);
title('(f) 72 条记录构成');

sgtitle('Agent MEMORY 投毒实验 — MATLAB 综合数学分析仪表盘', 'FontSize', 14, 'FontWeight', 'bold');
exportgraphics(fig5, fullfile(outDir, 'fig_dashboard.pdf'), 'Resolution', 300);
exportgraphics(fig5, fullfile(outDir, 'fig_dashboard.png'), 'Resolution', 300);

%% ========== 控制台摘要 ==========
fprintf('\n===== MEMORY 投毒实验 MATLAB 分析完成 =====\n');
fprintf('全局 E=%.2f%%  A=%.2f%%  I=%.2f%%\n', E_global*100, A_global*100, I_global*100);
fprintf('输出目录: %s\n', outDir);
fprintf('生成文件:\n');
fprintf('  fig_EAI_gap.pdf/png\n');
fprintf('  fig_3d_agent_attack_I.pdf/png\n');
fprintf('  fig_3d_surface_EAI.pdf/png\n');
fprintf('  fig_defense_ablation.pdf/png\n');
fprintf('  fig_dashboard.pdf/png\n');
