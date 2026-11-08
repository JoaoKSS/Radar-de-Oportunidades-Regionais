/* Radar de Oportunidades — renderização ECharts com identidade refinada:
   Paleta: Emerald Pro / Dark Tooltips / Gradientes suaves */
(function () {
  'use strict';

  var ACA = '#0d5f4c';
  var ACA_LIGHT = '#10b981';
  var OCRE = '#d97706';
  var CINZA = '#94a3b8';
  var BORDA = '#e2e8f0';
  var TINTA_FRACA = '#64748b';
  var RISCO = '#be123c';
  var FONTE = "'Plus Jakarta Sans', -apple-system, sans-serif";

  var st = {
    fontFamily: FONTE,
    color: [ACA, OCRE, CINZA],
    tooltip: {
      borderWidth: 1,
      borderColor: '#334155',
      backgroundColor: '#0f172a',
      padding: [8, 12],
      textStyle: { color: '#f8fafc', fontSize: 12.5, fontFamily: FONTE },
      extraCssText: 'box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3); border-radius: 6px;',
    },
  };
  function grade(base, grid) {
    return Object.assign({}, st, base, {
      grid: Object.assign(
        { left: 12, right: 18, top: 24, bottom: 8, containLabel: true },
        grid
      ),
    });
  }

  function render(id, op) {
    var el = document.getElementById(id);
    if (!el || !window.echarts) return null;
    var chart = echarts.init(el);
    chart.setOption(op);
    window.addEventListener('resize', function () {
      chart.resize();
    });
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        chart.resize();
      });
      ro.observe(el);
    }
    return chart;
  }

  function rotulosAno(arr) { return (arr || []).map(String); }

  /* ---------- painel do município ---------- */
  var R = window.__RADAR__;

  /* 1. Gráfico de População (Área com Gradiente) */
  if (R && R.pop && R.pop.valores.length) {
    render('chart-pop', grade({
      xAxis: { type: 'category', data: rotulosAno(R.pop.anos), boundaryGap: false,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: { color: TINTA_FRACA, fontSize: 11.5 }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f5f9' } },
               axisLabel: { color: TINTA_FRACA, fontSize: 11.5,
                            formatter: function (v) { return (v / 1000).toLocaleString('pt-BR') + ' mil'; } } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) { return '<strong>' + ps[0].axisValue + '</strong><br/>População: ' +
                   Number(ps[0].value).toLocaleString('pt-BR') + ' hab.'; } },
      series: [{
        type: 'line', data: R.pop.valores, smooth: true,
        lineStyle: { width: 2.8, color: ACA },
        symbol: 'circle', symbolSize: 6,
        itemStyle: { color: ACA, borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(13, 95, 76, 0.28)' },
            { offset: 1, color: 'rgba(13, 95, 76, 0.01)' }
          ])
        },
        markLine: { silent: true, symbol: 'none',
                    lineStyle: { color: '#cbd5e1', type: 'dashed' },
                    label: { show: false },
                    data: [{ yAxis: R.pop.valores[0] }] },
      }],
    }));
  }

  /* 2. Gráfico de PIB (Nominal vs Real Deflacionado) */
  if (R && R.pib && R.pib.nominal.length) {
    var demonom = R.pib.nominal.map(function (v) { return (v * 1000) / 1e9; });
    var ser = [{
      name: 'Nominal (IBGE)', type: 'line', data: demonom,
      smooth: true, symbol: 'circle', symbolSize: 5,
      lineStyle: { width: 2, color: CINZA, type: 'dashed' },
      itemStyle: { color: CINZA, borderColor: '#fff', borderWidth: 1.5 },
    }];
    if (R.tem_pib_real) {
      var real = R.pib.real.map(function (v) { return v == null ? null : (v * 1000) / 1e9; });
      ser.push({
        name: 'Real (deflacionado IPCA)', type: 'line', data: real,
        smooth: true, symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 3, color: ACA },
        itemStyle: { color: ACA, borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(13, 95, 76, 0.22)' },
            { offset: 1, color: 'rgba(13, 95, 76, 0.02)' }
          ])
        },
      });
    }
    render('chart-pib', grade({
      legend: { top: 0, right: 0, icon: 'circle', itemWidth: 8, textStyle: { color: TINTA_FRACA, fontSize: 12, fontWeight: 500 } },
      xAxis: { type: 'category', data: rotulosAno(R.pib.anos), boundaryGap: false,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: { color: TINTA_FRACA, fontSize: 11.5 }, axisTick: { show: false } },
      yAxis: { type: 'value', name: 'R$ bi', nameTextStyle: { color: TINTA_FRACA, fontSize: 11.5 },
               splitLine: { lineStyle: { color: '#f1f5f9' } },
               axisLabel: { color: TINTA_FRACA, fontSize: 11.5 } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) {
                   var t = '<strong>' + ps[0].axisValue + '</strong><br/>';
                   t += ps.map(function (p) {
                     return p.seriesName + ': <strong>R$ ' +
                       Number(p.value).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' bi</strong>';
                   }).join('<br/>');
                   return t;
                 } },
      series: ser,
    }, { top: 38 }));
  }

  /* 2.1 Composição Econômica Setorial (Donut Chart) */
  if (R && R.vab && R.vab.valores_mil && Object.keys(R.vab.valores_mil).length) {
    var vMap = R.vab.valores_mil;
    var vPct = R.vab.participacao_pct || {};
    var dadosDonut = [
      { name: 'Serviços', value: vMap.servicos || 0, pct: vPct.servicos || 0, itemStyle: { color: '#0d5f4c' } },
      { name: 'Indústria', value: vMap.industria || 0, pct: vPct.industria || 0, itemStyle: { color: '#0284c7' } },
      { name: 'Adm. Pública', value: vMap.admin || 0, pct: vPct.admin || 0, itemStyle: { color: '#d97706' } },
      { name: 'Agropecuária', value: vMap.agro || 0, pct: vPct.agro || 0, itemStyle: { color: '#10b981' } },
    ].filter(function (d) { return d.value > 0; });

    render('chart-setores', {
      tooltip: {
        trigger: 'item',
        backgroundColor: '#0f172a',
        borderColor: '#334155',
        textStyle: { color: '#f8fafc', fontSize: 12 },
        formatter: function (p) {
          var bi = p.value / 1e6;
          var vFmt = bi >= 1 ? bi.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' bi' : (p.value / 1e3).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' mi';
          return '<strong>' + p.name + '</strong><br/>VAB: R$ ' + vFmt + ' (' + Number(p.data.pct).toFixed(1) + '%)';
        }
      },
      legend: {
        bottom: 4,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: TINTA_FRACA, fontSize: 11.5, fontFamily: FONTE },
      },
      series: [{
        name: 'VAB Setorial',
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'inside',
          formatter: function (p) {
            return p.percent >= 8 ? p.percent.toFixed(0) + '%' : '';
          },
          fontSize: 11,
          fontWeight: 700,
          color: '#ffffff'
        },
        emphasis: {
          label: { show: true, fontSize: 12, fontWeight: 700 }
        },
        data: dadosDonut
      }]
    });
  }
  if (R && R.ipca && R.ipca.meses.length) {
    render('chart-ipca', grade({
      xAxis: { type: 'category', data: R.ipca.meses,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: { color: TINTA_FRACA, interval: 3, fontSize: 11 }, axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 11 },
               splitLine: { lineStyle: { color: '#f1f5f9' } } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) { return '<strong>' + ps[0].axisValue + '</strong><br/>IPCA no mês: <strong>' +
                   Number(ps[0].value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + '%</strong>'; } },
      series: [{
        type: 'bar', data: R.ipca.variacao.map(function (v) {
          return {
            value: v,
            itemStyle: {
              color: v >= 0 ? ACA_LIGHT : RISCO,
              borderRadius: v >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4]
            }
          };
        }),
        barWidth: '55%',
      }],
    }));
  }

  /* 4. IPCA 12 Meses (Linha contínua com markline de meta) */
  if (R && R.ipca12 && R.ipca12.meses.length) {
    render('chart-ipca12', grade({
      xAxis: { type: 'category', data: R.ipca12.meses, boundaryGap: false,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: { color: TINTA_FRACA, interval: 3, fontSize: 11 }, axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 11 },
               splitLine: { lineStyle: { color: '#f1f5f9' } } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) { return '<strong>' + ps[0].axisValue + '</strong><br/>Acumulado 12 meses: <strong>' +
                   Number(ps[0].value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + '%</strong>'; } },
      series: [{
        type: 'line', data: R.ipca12.valores, smooth: true,
        lineStyle: { width: 2.8, color: ACA },
        itemStyle: { color: ACA, borderColor: '#fff', borderWidth: 2 },
        symbol: 'circle', symbolSize: 5,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(13, 95, 76, 0.18)' },
            { offset: 1, color: 'rgba(13, 95, 76, 0.01)' }
          ])
        },
        markLine: { silent: true, symbol: 'none',
                    data: [{ yAxis: 3, lineStyle: { color: '#cbd5e1', type: 'dashed' },
                             label: { show: true, formatter: 'meta 3,0%', color: TINTA_FRACA, position: 'insideEndTop' } }] },
      }],
    }));
  }

  /* 5. Crédito Empresarial (Juros de Capital de Giro x Inadimplência PJ - Duplo Eixo) */
  if (R && R.credito && R.credito.meses && R.credito.meses.length) {
    var cMeses = R.credito.meses;
    var cJuros = R.credito.juros_giro;
    var cInad = R.credito.inadimplencia;

    render('chart-credito-pj', grade({
      legend: {
        top: 2,
        right: 0,
        icon: 'circle',
        itemWidth: 8,
        itemGap: 16,
        textStyle: { color: TINTA_FRACA, fontSize: 11.5, fontWeight: 500 }
      },
      xAxis: { type: 'category', data: cMeses, boundaryGap: false,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: { color: TINTA_FRACA, interval: 3, fontSize: 11 }, axisTick: { show: false } },
      yAxis: [
        {
          type: 'value', name: 'Juros Giro (% a.a.)', position: 'left',
          nameTextStyle: { color: TINTA_FRACA, fontSize: 11, padding: [0, 0, 8, 0] },
          axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 10.5 },
          splitLine: { lineStyle: { color: '#f1f5f9' } }
        },
        {
          type: 'value', name: 'Inadimplência PJ', position: 'right',
          nameTextStyle: { color: TINTA_FRACA, fontSize: 11, padding: [0, 0, 8, 0] },
          axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 10.5 },
          splitLine: { show: false }
        }
      ],
      tooltip: {
        trigger: 'axis',
        formatter: function (ps) {
          var t = '<strong>' + ps[0].axisValue + '</strong><br/>';
          ps.forEach(function (p) {
            t += p.marker + ' ' + p.seriesName + ': <strong>' +
                 Number(p.value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + '%</strong><br/>';
          });
          return t;
        }
      },
      series: [
        {
          name: 'Juros Capital de Giro', type: 'line', yAxisIndex: 0,
          data: cJuros, smooth: true,
          lineStyle: { width: 2.5, color: '#0284c7' },
          itemStyle: { color: '#0284c7' },
          symbol: 'circle', symbolSize: 5
        },
        {
          name: 'Inadimplência PJ', type: 'line', yAxisIndex: 1,
          data: cInad, smooth: true,
          lineStyle: { width: 2.5, color: '#dc2626', type: 'dashed' },
          itemStyle: { color: '#dc2626' },
          symbol: 'circle', symbolSize: 5
        }
      ]
    }, { top: 58, bottom: 12 }));
  }

  /* ---------- mapa de localização (IBGE Malhas) ---------- */
  if (R && R.geo && document.getElementById('chart-mapa')) {
    fetch('/api/malha/brasil')
      .then(function (r) { return r.json(); })
      .then(function (malha) {
        echarts.registerMap('brasil-uf', malha);
        var M = R.mapa || {};
        var viz = M.vizinhos || [];
        var maxPib = 0;
        viz.forEach(function (v) { if (v.pib > maxPib) maxPib = v.pib; });

        var geoCfg = {
          map: 'brasil-uf',
          roam: true,
          scaleLimit: {
            min: 0.85, // Enquadramento perfeito: mostra o Brasil inteiro preenchendo a área útil sem encolher demais
            max: 12
          },
          silent: false,
          selectedMode: false,
          layoutCenter: ['50%', '50%'],
          layoutSize: '100%',
          itemStyle: {
            areaColor: '#f1f5f9',
            borderColor: '#cbd5e1',
            borderWidth: 0.8,
          },
          emphasis: {
            disabled: true,
          },
          regions: [{
            name: R.uf,
            itemStyle: { areaColor: '#ffffff', borderColor: '#0d5f4c', borderWidth: 1.5 },
            label: { show: true, color: '#0d5f4c', fontSize: 12, fontWeight: 700 },
            emphasis: {
              disabled: true,
              itemStyle: { areaColor: '#ffffff' },
            },
          }],
        };
        if (M.bbox) {
          var cx = (M.bbox.min_lon + M.bbox.max_lon) / 2;
          var cy = (M.bbox.min_lat + M.bbox.max_lat) / 2;
          var diag = Math.max(M.bbox.max_lon - M.bbox.min_lon, (M.bbox.max_lat - M.bbox.min_lat) * 1.4);
          geoCfg.center = [cx, cy];
          geoCfg.zoom = Math.max(1.1, Math.min(8.5, 46 / (diag + 5.5)));
        }

        var series = [];
        series.push({
          type: 'map',
          map: 'brasil-uf',
          geoIndex: 0,
          silent: true,
          data: [{
            name: R.uf,
            itemStyle: {
              areaColor: '#ffffff',
              borderColor: '#0d5f4c',
              borderWidth: 2,
            },
            emphasis: {
              disabled: true,
              itemStyle: { areaColor: '#ffffff' }
            }
          }]
        });

        // Adiciona uma camada de linha para o contorno do estado selecionado
        var ufFeature = (malha.features || []).find(function (f) {
          return f.properties && f.properties.name === R.uf;
        });
        if (ufFeature && ufFeature.geometry) {
          var geom = ufFeature.geometry;
          var lineCoords = [];
          if (geom.type === 'Polygon') {
            lineCoords = geom.coordinates;
          } else if (geom.type === 'MultiPolygon') {
            geom.coordinates.forEach(function (poly) {
              lineCoords = lineCoords.concat(poly);
            });
          }
          if (lineCoords.length) {
            series.push({
              type: 'lines',
              coordinateSystem: 'geo',
              polyline: true,
              silent: true,
              zlevel: 2,
              lineStyle: {
                color: '#0d5f4c',
                width: 2.2,
                opacity: 1
              },
              data: lineCoords.map(function (ring) {
                return { coords: ring };
              })
            });
          }
        }

        if (viz.length) {
          series.push({
            name: 'Municípios do estado',
            type: 'scatter', coordinateSystem: 'geo',
            symbolSize: function (val) {
              return 4 + 20 * Math.sqrt((val[2] || 0) / (maxPib || 1));
            },
            itemStyle: {
              color: 'rgba(13,95,76,.35)',
              borderColor: 'rgba(13,95,76,.65)',
              borderWidth: 0.75,
            },
            emphasis: {
              itemStyle: { color: 'rgba(13,95,76,.85)', borderColor: '#0d5f4c', borderWidth: 1.5 },
            },
            data: viz.map(function (v) {
              return { name: v.nome, value: [v.lon, v.lat, v.pib] };
            }),
            zlevel: 3,
          });
        }
        series.push({
          type: 'effectScatter', coordinateSystem: 'geo',
          rippleEffect: { scale: 3.5, brushType: 'stroke', period: 3 },
          symbolSize: 14, zlevel: 4,
          itemStyle: { color: '#be123c', shadowBlur: 8, shadowColor: 'rgba(190, 18, 60, 0.4)' },
          label: {
            show: true, formatter: R.nome, position: 'top', distance: 6,
            fontSize: 12, fontWeight: 700, color: '#0f172a',
            backgroundColor: 'rgba(255,255,255,0.92)',
            borderColor: '#e2e8f0', borderWidth: 1,
            borderRadius: 4, padding: [3, 7],
            shadowBlur: 4, shadowColor: 'rgba(0,0,0,0.06)'
          },
          data: [{ name: R.nome, value: [R.geo.lon, R.geo.lat] }],
        });

        var centroOriginal = geoCfg.center ? [geoCfg.center[0], geoCfg.center[1]] : null;
        var zoomOriginal = geoCfg.zoom || 1.3;

        var mapChart = render('chart-mapa', {
          tooltip: {
            trigger: 'item',
            backgroundColor: '#0f172a',
            borderColor: '#334155',
            textStyle: { color: '#f8fafc', fontSize: 12 },
            formatter: function (p) {
              if (p.value && p.value[2]) {
                var bi = p.value[2] / 1e6;
                return '<strong>' + p.name + '</strong><br/>PIB: R$ ' + bi.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' bi';
              }
              return '<strong>' + p.name + '</strong>';
            },
          },
          geo: geoCfg,
          series: series,
        });

        // Botão para restaurar a visão e enquadramento original do estado
        var btnReset = document.getElementById('btn-centralizar-mapa');
        if (btnReset && mapChart) {
          mapChart.on('georoam', function () {
            btnReset.classList.add('visivel');
          });

          btnReset.addEventListener('click', function () {
            mapChart.setOption({
              geo: {
                center: centroOriginal,
                zoom: zoomOriginal,
              }
            });
            btnReset.classList.remove('visivel');
          });
        }
        // Intercepta e suaviza a aceleração excessiva do scroll do mouse
        var mapDom = document.getElementById('chart-mapa');
        if (mapDom && mapChart) {
          mapDom.addEventListener('wheel', function (e) {
            e.preventDefault();
            e.stopPropagation();

            var op = mapChart.getOption();
            var currGeo = (op.geo && op.geo[0]) || {};
            var currentZoom = currGeo.zoom || zoomOriginal || 1;
            var delta = e.deltaY > 0 ? -1 : 1;
            var factor = delta > 0 ? 1.07 : 0.93;
            var minZ = (geoCfg.scaleLimit && geoCfg.scaleLimit.min) || 0.75;
            var maxZ = (geoCfg.scaleLimit && geoCfg.scaleLimit.max) || 12;
            var newZoom = Math.max(minZ, Math.min(maxZ, currentZoom * factor));

            if (newZoom !== currentZoom) {
              mapChart.setOption({
                geo: {
                  zoom: newZoom
                }
              });
              if (btnReset) btnReset.classList.add('visivel');
            }
          }, { passive: false });
        }
      })
      .catch(function () {});
  }

  /* ---------- comparador ---------- */
  var G = window.__COMPARAR__;
  if (G && G.labels && G.labels.length) {
    render('chart-pc', grade({
      xAxis: { type: 'category', data: G.labels,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: {
                 color: TINTA_FRACA,
                 fontSize: 11,
                 fontWeight: 600,
                 interval: 0,
                 width: 90,
                 overflow: 'truncate',
                 ellipsis: '…'
               },
               axisTick: { show: false } },
      yAxis: { type: 'value',
               splitLine: { lineStyle: { color: '#f1f5f9' } },
               axisLabel: { color: TINTA_FRACA, fontSize: 11.5,
                            formatter: function (v) { return Number(v).toLocaleString('pt-BR'); } } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) { return '<strong>' + ps[0].axisValue + '</strong><br/>PIB per capita: <strong>R$ ' +
                   Number(ps[0].value).toLocaleString('pt-BR') + ' mil/hab</strong>'; } },
      series: [{
        type: 'bar', data: G.pib_pc, barWidth: '38%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#0d5f4c' },
            { offset: 1, color: '#094336' }
          ]),
          borderRadius: [6, 6, 0, 0],
          shadowColor: 'rgba(13, 95, 76, 0.15)',
          shadowBlur: 6,
        }
      }],
    }, { bottom: 32 }));

    render('chart-cresc', grade({
      xAxis: { type: 'category', data: G.labels,
               axisLine: { lineStyle: { color: BORDA } },
               axisLabel: {
                 color: TINTA_FRACA,
                 fontSize: 11,
                 fontWeight: 600,
                 interval: 0,
                 width: 90,
                 overflow: 'truncate',
                 ellipsis: '…'
               },
               axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 11.5 },
               splitLine: { lineStyle: { color: '#f1f5f9' } } },
      tooltip: { trigger: 'axis',
                 formatter: function (ps) { return '<strong>' + ps[0].axisValue + '</strong><br/>Cresc. Populacional: <strong>' +
                   Number(ps[0].value).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%</strong>'; } },
      series: [{
        type: 'bar', data: G.cresc_pop.map(function (v) {
          return {
            value: v,
            itemStyle: {
              color: v >= 0 ? '#10b981' : '#be123c',
              borderRadius: v >= 0 ? [6, 6, 0, 0] : [0, 0, 6, 6],
              shadowColor: v >= 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(190, 18, 60, 0.2)',
              shadowBlur: 6,
            }
          };
        }),
        barWidth: '38%'
      }],
    }, { bottom: 32 }));

    /* 3. Vocação Econômica Comparativa (VAB Setorial 100% Empilhado) */
    if (G.vab && G.vab.length) {
      render('chart-vab-comp', grade({
        legend: {
          top: 0,
          right: 0,
          icon: 'circle',
          itemWidth: 8,
          itemGap: 14,
          textStyle: { color: TINTA_FRACA, fontSize: 11.5, fontWeight: 500 }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: function (ps) {
            var t = '<strong>' + ps[0].axisValue + '</strong><br/>';
            ps.forEach(function (p) {
              t += p.marker + ' ' + p.seriesName + ': <strong>' + Number(p.value).toFixed(1) + '%</strong><br/>';
            });
            return t;
          }
        },
        xAxis: {
          type: 'category',
          data: G.labels,
          axisLine: { lineStyle: { color: BORDA } },
          axisLabel: { color: TINTA_FRACA, fontSize: 12, fontWeight: 600 },
          axisTick: { show: false }
        },
        yAxis: {
          type: 'value',
          max: 100,
          axisLabel: { color: TINTA_FRACA, formatter: '{value}%', fontSize: 11 },
          splitLine: { lineStyle: { color: '#f1f5f9' } }
        },
        series: [
          {
            name: 'Serviços', type: 'bar', stack: 'total',
            data: G.vab.map(function (d) { return d.servicos; }),
            itemStyle: { color: '#0d5f4c' }, barWidth: '42%'
          },
          {
            name: 'Indústria', type: 'bar', stack: 'total',
            data: G.vab.map(function (d) { return d.industria; }),
            itemStyle: { color: '#0284c7' }
          },
          {
            name: 'Adm. Pública', type: 'bar', stack: 'total',
            data: G.vab.map(function (d) { return d.admin; }),
            itemStyle: { color: '#d97706' }
          },
          {
            name: 'Agropecuária', type: 'bar', stack: 'total',
            data: G.vab.map(function (d) { return d.agro; }),
            itemStyle: { color: '#10b981' }
          }
        ]
      }, { top: 38, bottom: 12 }));
    }
  }

  /* ---------- autocomplete (início + comparador) ---------- */
  var entrada = document.getElementById('busca-entrada');
  var sugestoes = document.getElementById('busca-sugestoes');
  if (entrada && sugestoes) {
    var timer = null;
    var selecionados = (window.__COMPARADOR__ && window.__COMPARADOR__.idsSelecionados) || null;
    var pilhas = document.getElementById('pilhas');
    var btn = document.getElementById('comparar');

    function atualizarBotao() {
      if (btn) btn.disabled = document.querySelectorAll('.pilha').length < 2;
    }
    atualizarBotao();

    // Event delegation para remover as pilhas tanto iniciais (renderizadas pelo servidor) quanto criadas dinamicamente
    if (pilhas) {
      pilhas.addEventListener('click', function (ev) {
        var btnRemover = ev.target.closest('button');
        if (btnRemover) {
          var p = btnRemover.closest('.pilha');
          if (p) {
            p.remove();
            atualizarBotao();
          }
        }
      });
    }

    function abrir(nome, id, uf) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#';
      var spanNome = document.createElement('span'); spanNome.textContent = nome;
      var spanUF = document.createElement('span'); spanUF.className = 'uf'; spanUF.textContent = uf;
      a.append(spanNome, spanUF);
      a.addEventListener('click', function (ev) {
        ev.preventDefault();
        sugestoes.hidden = true; entrada.value = '';
        if (selecionados === null) { location.href = '/municipio/' + id; return; }
        if (document.querySelector('.pilha[data-id="' + id + '"]')) return;
        var p = document.createElement('span');
        p.className = 'pilha'; p.dataset.id = id;
        var s = document.createElement('span'); s.className = 'pilha-nome'; s.textContent = nome + ' · ' + uf;
        var x = document.createElement('button'); x.type = 'button'; x.title = 'Remover'; x.textContent = '×';
        p.append(s, x); pilhas.append(p);
        atualizarBotao();
      });
      li.append(a); sugestoes.append(li);
    }

    entrada.addEventListener('input', function () {
      var q = entrada.value.trim();
      clearTimeout(timer);
      if (q.length < 2) { sugestoes.hidden = true; return; }
      timer = setTimeout(async function () {
        try {
          var r = await fetch('/api/localidades?q=' + encodeURIComponent(q));
          var jr = await r.json();
          sugestoes.innerHTML = '';
          if (!jr.length) { sugestoes.hidden = true; return; }
          jr.slice(0, 9).forEach(function (m) { abrir(m.nome, m.id, m.uf); });
          sugestoes.hidden = false;
        } catch { sugestoes.hidden = true; }
      }, 140);
    });
    // Trata tecla Escape globalmente (mesmo se o foco estiver fora do input)
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') {
        var mudouAlgo = false;
        if (!sugestoes.hidden) {
          sugestoes.hidden = true;
          mudouAlgo = true;
        }
        if (entrada.value) {
          entrada.value = '';
          mudouAlgo = true;
        }
        if (mudouAlgo) {
          ev.preventDefault();
          entrada.focus();
        } else if (document.activeElement === entrada) {
          entrada.blur();
        }
      }
    });

    document.addEventListener('click', function (ev) {
      if (!ev.target.closest('.busca-terminal') && !ev.target.closest('.busca-wrap') && !ev.target.closest('.busca')) {
        sugestoes.hidden = true;
      }
    });
    if (btn) btn.addEventListener('click', function () {
      var ids = [...document.querySelectorAll('.pilha')].map(function (p) { return p.dataset.id; });
      if (ids.length >= 2) location.href = '/comparar?ids=' + ids.join(',');
    });
  }
})();
