// ==============================================================================
// EXPORTAÇÃO MAPBIOMAS COLEÇÃO 11 (2004, 2014 E 2024) — TI YANOMAMI
// Cole este código em: https://code.earthengine.google.com/
// Depois clique em "Run" e vá na aba "Tasks" (à direita) para clicar em "RUN"
// nas 3 tarefas de exportação para o seu Google Drive.
// ==============================================================================

// 1. Retângulo envolvente exato da Terra Indígena Yanomami (EPSG:4326)
// (O WebGIS já faz o recorte exato pelo polígono YANOMAMI.geojson automaticamente)
var regiaoYanomami = ee.Geometry.Rectangle([-66.48, -0.33, -61.33, 4.30]);

// 2. Asset oficial da Coleção 11 do MapBiomas Brasil (Cobertura 30m)
var assetId = 'projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_coverage_v3';
var mapbiomas = ee.Image(assetId);

// 3. Anos desejados
var anos = [2004, 2014, 2024];

// Centraliza o mapa do GEE na TI Yanomami
Map.centerObject(regiaoYanomami, 7);

// 4. Adiciona ao mapa e cria uma tarefa de exportação GeoTIFF para cada ano
anos.forEach(function(ano) {
  var banda = 'classification_' + ano;
  var imagemAno = mapbiomas.select(banda).clip(regiaoYanomami).toByte();

  // Visualiza apenas a classe 30 (Mineração) em roxo para conferência rápida no GEE
  var mineracao = imagemAno.eq(30).selfMask();
  Map.addLayer(mineracao, {palette: ['#9b59b6']}, 'Mineração ' + ano, ano === 2024);

  // Exporta o GeoTIFF completo (todas as classes) para o Google Drive
  Export.image.toDrive({
    image: imagemAno,
    description: 'yanomami_mapbiomas_col11_' + ano,
    folder: 'MapBiomas_Yanomami',
    fileNamePrefix: 'yanomami_mapbiomas_col11_' + ano,
    region: regiaoYanomami,
    scale: 30,
    crs: 'EPSG:4674',
    maxPixels: 1e13,
    fileFormat: 'GeoTIFF',
    formatOptions: {
      cloudOptimized: true
    }
  });
});

print('Tarefas criadas! Clique na aba "Tasks" (canto superior direito) e clique em RUN nos 3 anos.');
