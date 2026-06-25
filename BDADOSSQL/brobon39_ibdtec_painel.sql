-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Tempo de geração: 17/06/2026 às 16:38
-- Versão do servidor: 5.7.44-48
-- Versão do PHP: 8.3.31

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `brobon39_ibdtec_painel`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `agenda_eventos`
--

CREATE TABLE `agenda_eventos` (
  `id` int(11) NOT NULL,
  `titulo` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `data_evento` date NOT NULL,
  `data_fim` date DEFAULT NULL,
  `data_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `tipo_evento` varchar(20) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'reuniao',
  `local_evento` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `horario` varchar(10) COLLATE utf8_unicode_ci DEFAULT NULL,
  `criado_por` varchar(120) COLLATE utf8_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `arquivos_painel`
--

CREATE TABLE `arquivos_painel` (
  `id` int(11) NOT NULL,
  `nome_original` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `caminho_sistema` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `bloco` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
  `categoria` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
  `tipo` varchar(50) COLLATE utf8_unicode_ci NOT NULL,
  `pasta_pai_id` int(11) DEFAULT NULL,
  `criado_por` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `deletado` tinyint(1) DEFAULT '0',
  `deletado_em` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `data_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Despejando dados para a tabela `arquivos_painel`
--

INSERT INTO `arquivos_painel` (`id`, `nome_original`, `caminho_sistema`, `bloco`, `categoria`, `tipo`, `pasta_pai_id`, `criado_por`, `deletado`, `deletado_em`, `data_registro`) VALUES
(1, 'Projetos', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-09 21:12:35', '2026-06-05 19:34:00'),
(2, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:52:20.835876', '2026-06-05 19:34:40'),
(3, 'Documentos', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-09 21:30:01', '2026-06-05 19:40:17'),
(4, 'Certidões', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-09 21:29:55', '2026-06-05 19:40:26'),
(5, 'Fomento', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-09 21:29:47', '2026-06-05 19:40:45'),
(6, 'Empresa', NULL, 'jp2_business', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-05 19:40:58'),
(7, 'Financeiro', NULL, 'jp2_business', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-05 19:41:10'),
(8, 'Arquivos', NULL, 'jp2_business', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-05 19:41:24'),
(9, 'Administrativo', NULL, 'jp2_business', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-05 19:41:36'),
(10, 'Arraia Solidário', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:42:22'),
(11, 'Ciência e Tecnologia', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:42:36'),
(12, 'Cinema Céu Aberto', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:42:47'),
(13, 'Cinema de Rua', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:42:57'),
(14, 'Comunidade Festa Integração Escolas', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:43:12'),
(15, 'Corrida de Verão', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:43:30'),
(16, 'Corrida Passos do Bem', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:43:43'),
(17, 'Luta Artes Marciais', NULL, 'instituto', 'raiz', 'pasta', 1, 'Petrick Martins', 0, NULL, '2026-06-05 19:43:55'),
(18, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 10, 'Petrick Martins', 0, NULL, '2026-06-05 19:44:10'),
(19, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 11, 'Petrick Martins', 0, NULL, '2026-06-05 19:44:29'),
(20, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 12, 'Petrick Martins', 0, NULL, '2026-06-05 19:44:46'),
(21, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 13, 'Petrick Martins', 0, NULL, '2026-06-05 19:45:04'),
(22, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 14, 'Petrick Martins', 0, NULL, '2026-06-05 19:45:25'),
(23, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 15, 'Petrick Martins', 0, NULL, '2026-06-05 19:45:52'),
(24, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 16, 'Petrick Martins', 0, NULL, '2026-06-05 19:46:16'),
(25, 'Portifólio', NULL, 'instituto', 'raiz', 'pasta', 17, 'Petrick Martins', 0, NULL, '2026-06-05 19:46:37'),
(26, 'Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '/static/uploads/5dcc91e2345e447ca29ad67bb9ecfc47_Arrai_Solidrio_2026_-_Portflio_Vila_Planalto-1.pdf', 'instituto', 'raiz', 'arquivo', 18, 'Petrick Martins', 1, '2026-06-08T21:23:24.936104', '2026-06-05 19:47:29'),
(27, 'Evento Ciencia e Tecnologia.pdf', '/static/uploads/641eacee362247c1b013c91848f3c70f_Evento_Ciencia_e_Tecnologia.pdf', 'instituto', 'raiz', 'arquivo', 19, 'Petrick Martins', 1, '2026-06-08T21:25:39.861596', '2026-06-05 19:48:09'),
(28, 'Cinema à Céu Aberto Lago Paranoá_2.0.pdf', '/static/uploads/0143508481b94f3ca63190603480ce63_Cinema__Cu_Aberto_Lago_Parano_2.0.pdf', 'instituto', 'raiz', 'arquivo', 20, 'Petrick Martins', 1, '2026-06-08T21:26:09.826999', '2026-06-05 19:48:57'),
(29, 'CineMovie Project_2.0.pdf', '/static/uploads/f65479efd65d42ae800c7ef5eb1428aa_CineMovie_Project_2.0.pdf', 'instituto', 'raiz', 'arquivo', 21, 'Petrick Martins', 1, '2026-06-08T21:26:39.176621', '2026-06-05 19:49:33'),
(30, 'Comunidade em Festa.pdf', '/static/uploads/ac6cfe00a6a443ad8be2a2ac86273696_Comunidade_em_Festa.pdf', 'instituto', 'raiz', 'arquivo', 22, 'Petrick Martins', 1, '2026-06-08T21:27:09.006601', '2026-06-05 19:50:21'),
(31, 'BrandBook_Imagens_Material_Corrida_do_Ver__o.png', '/static/uploads/91b9507684594b229dd2ab70d3680c24_BrandBook_Imagens_Material_Corrida_do_Ver__o.png', 'instituto', 'raiz', 'arquivo', 23, 'Petrick Martins', 1, '2026-06-05T19:53:12.226344', '2026-06-05 19:51:42'),
(32, 'Planta 3D', NULL, 'instituto', 'raiz', 'pasta', 23, 'Petrick Martins', 1, '2026-06-05T19:52:58.955919', '2026-06-05 19:52:09'),
(33, 'Planta 3D', NULL, 'instituto', 'raiz', 'pasta', 15, 'Petrick Martins', 0, NULL, '2026-06-05 19:53:36'),
(34, 'BrandBook_Imagens_Material_Corrida_do_Ver__o.png', '/static/uploads/846abe5a63b44b3b867090b58ae606ed_BrandBook_Imagens_Material_Corrida_do_Ver__o.png', 'instituto', 'raiz', 'arquivo', 15, 'Petrick Martins', 1, '2026-06-08T21:27:35.846769', '2026-06-05 19:53:48'),
(35, 'Circuito Corrida de Verão.pdf', '/static/uploads/b1cef01e8c7a4dbda5af3e70fa11490c_Circuito_Corrida_de_Vero.pdf', 'instituto', 'raiz', 'arquivo', 23, 'Petrick Martins', 1, '2026-06-08T21:32:09.828891', '2026-06-05 19:54:34'),
(36, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:52:06.528627', '2026-06-05 20:07:26'),
(37, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:51:51.235194', '2026-06-05 20:20:05'),
(38, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:51:36.859758', '2026-06-05 20:21:06'),
(39, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:51:22.436752', '2026-06-05 20:29:57'),
(40, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:51:07.813001', '2026-06-05 20:33:07'),
(41, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T20:52:52.237586', '2026-06-05 20:52:36'),
(42, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T21:17:06.813367', '2026-06-05 21:03:41'),
(43, 'Registro Civil', 'https://www.google.com', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T21:48:38.776488', '2026-06-05 21:17:18'),
(44, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-05T21:49:04.088157', '2026-06-05 21:26:47'),
(45, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-09T02:36:33.220579', '2026-06-05 22:05:05'),
(46, '01 Planta 3d.zip', '/static/uploads/b733806396584a0cb83ebcf8fcb39be7_01_Planta_3d.zip', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:27:51.636963', '2026-06-06 13:00:26'),
(47, 'IMG-20260429-WA0047.jpg', '/static/uploads/7eec0e55507a4c5d930dd67049feb101_IMG-20260429-WA0047.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:28:05.512297', '2026-06-06 13:03:34'),
(48, 'IMG-20260429-WA0048.jpg', '/static/uploads/d09e2c6d50534a2aa7ce499660508924_IMG-20260429-WA0048.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:28:18.114230', '2026-06-06 13:03:52'),
(49, 'IMG-20260429-WA0049.jpg', '/static/uploads/d16b17a909a5454ba4e7fd18cb4997d9_IMG-20260429-WA0049.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:28:32.760346', '2026-06-06 13:04:19'),
(50, 'IMG-20260429-WA0050.jpg', '/static/uploads/efbec462d56d48dba07679eabc1e716e_IMG-20260429-WA0050.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:28:49.285052', '2026-06-06 13:04:30'),
(51, 'IMG-20260429-WA0051.jpg', '/static/uploads/11d984a66aac43fbbb31a05f1742c6e6_IMG-20260429-WA0051.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:29:02.838569', '2026-06-06 13:04:53'),
(52, 'IMG-20260429-WA0052.jpg', '/static/uploads/042202896418465383c10122df101fa1_IMG-20260429-WA0052.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:29:15.764043', '2026-06-06 13:05:15'),
(53, 'IMG-20260429-WA0053.jpg', '/static/uploads/2fc38adf0c404af499e5205264729392_IMG-20260429-WA0053.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:29:28.232585', '2026-06-06 13:06:01'),
(54, 'IMG-20260429-WA0054.jpg', '/static/uploads/52550508836b47b0ab721dca6b004a06_IMG-20260429-WA0054.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:29:40.054230', '2026-06-06 13:06:15'),
(55, 'IMG-20260429-WA0055.jpg', '/static/uploads/15c9136acbdd4801aaa7016fe9fac09d_IMG-20260429-WA0055.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:29:55.463406', '2026-06-06 13:06:50'),
(56, 'IMG-20260429-WA0056.jpg', '/static/uploads/d5b8cb16d68d47c7b59e4a8cf3269e3f_IMG-20260429-WA0056.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:30:08.105991', '2026-06-06 13:08:05'),
(57, 'IMG-20260429-WA0057.jpg', '/static/uploads/b700aa863b9247a7a4aaeffb85b21720_IMG-20260429-WA0057.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:30:21.285155', '2026-06-06 13:08:19'),
(58, 'IMG-20260429-WA0058.jpg', '/static/uploads/1a8f3ec845584901ad88024abe80472e_IMG-20260429-WA0058.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:30:33.294996', '2026-06-06 13:08:48'),
(59, 'IMG-20260429-WA0059.jpg', '/static/uploads/6411275dfbbd4705b92c57d6f1822089_IMG-20260429-WA0059.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:30:45.705538', '2026-06-06 13:09:02'),
(60, 'IMG-20260429-WA0060.jpg', '/static/uploads/7dafd7214aac4456bf6f86ebe9638e3c_IMG-20260429-WA0060.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:30:58.143562', '2026-06-06 13:09:16'),
(61, 'IMG-20260429-WA0061.jpg', '/static/uploads/1bbb9261f7ca440c84ffb8dff7d50c96_IMG-20260429-WA0061.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:31:10.984188', '2026-06-06 13:09:28'),
(62, 'IMG-20260429-WA0062.jpg', '/static/uploads/8fe6548915704fe2b4523b4359b86f6c_IMG-20260429-WA0062.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:31:23.042084', '2026-06-06 13:09:43'),
(63, 'IMG-20260429-WA0063.jpg', '/static/uploads/f0d6972db0de40758642654e4c2eea80_IMG-20260429-WA0063.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:31:36.144256', '2026-06-06 13:09:56'),
(64, 'IMG-20260429-WA0064.jpg', '/static/uploads/dffd6c2492924b53bf88f17e40bf8e77_IMG-20260429-WA0064.jpg', 'instituto', 'raiz', 'arquivo', 33, 'Petrick Martins', 1, '2026-06-08T21:31:48.079049', '2026-06-06 13:10:11'),
(65, 'Circuito Passos do Bem Run Series.pdf', '/static/uploads/8c3ec97aea2949eb83c432568cf6dbe0_Circuito_Passos_do_Bem_Run_Series.pdf', 'instituto', 'raiz', 'arquivo', 24, 'Petrick Martins', 1, '2026-06-08T21:32:45.744726', '2026-06-06 13:11:39'),
(66, 'IMG-20260429-WA0064.jpg', '/static/uploads/8b8dbddbc8c446de9699f072e7fdcacd_IMG-20260429-WA0064.jpg', 'instituto', 'raiz', 'arquivo', 25, 'Petrick Martins', 1, '2026-06-06T14:35:41.985715', '2026-06-06 14:35:17'),
(67, 'IMG-20260429-WA0064.jpg', '/static/uploads/181febb5d75e4b8aa276ec6eea78c0c5_IMG-20260429-WA0064.jpg', 'instituto', 'raiz', 'arquivo', 25, 'Petrick Martins', 1, '2026-06-06T14:42:24.430405', '2026-06-06 14:41:52'),
(68, 'IMG-20260429-WA0063.jpg', '/static/uploads/b836aeda023046b49dfbcd64278f0128_IMG-20260429-WA0063.jpg', 'instituto', 'raiz', 'arquivo', 25, 'Petrick Martins', 1, '2026-06-06T14:42:38.531928', '2026-06-06 14:41:52'),
(69, 'IMG-20260429-WA0062.jpg', '/static/uploads/01486f39b299471ebe38dd139ae6234e_IMG-20260429-WA0062.jpg', 'instituto', 'raiz', 'arquivo', 25, 'Petrick Martins', 1, '2026-06-06T14:42:52.159891', '2026-06-06 14:41:52'),
(70, 'Logo e Bunner Luta', NULL, 'instituto', 'raiz', 'pasta', 17, 'Petrick Martins', 0, NULL, '2026-06-08 10:44:43'),
(71, 'Planta 3D Luta', NULL, 'instituto', 'raiz', 'pasta', 17, 'Petrick Martins', 0, NULL, '2026-06-08 10:46:00'),
(72, 'Logo Evento.jpeg', '/static/uploads/792770c7205a496a9a192755510c8395_Logo_Evento.jpeg', 'instituto', 'raiz', 'arquivo', 70, 'Petrick Martins', 1, '2026-06-08T21:33:16.871712', '2026-06-08 10:49:51'),
(73, 'Baner Fight Community.png', '/static/uploads/807e3afb3fee4a6780bdeb8add6d89f0_Baner_Fight_Community.png', 'instituto', 'raiz', 'arquivo', 70, 'Petrick Martins', 1, '2026-06-08T21:33:29.137229', '2026-06-08 10:49:51'),
(74, 'Imagem 3d_3.jpeg', '/static/uploads/a7806d61e34e44328132144806f6198f_Imagem_3d_3.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T20:44:28.449575', '2026-06-08 10:57:25'),
(75, 'Imagem 3d_2.jpeg', '/static/uploads/2a0843e617214f13a5244e479f767b01_Imagem_3d_2.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:33:49.140467', '2026-06-08 10:57:25'),
(76, 'Imagem 3d_1.jpeg', '/static/uploads/004d2ea323284d1baadb99366bce8171_Imagem_3d_1.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:50:45.518833', '2026-06-08 10:57:25'),
(77, 'Imagem 3d_7.jpeg', '/static/uploads/136a08af16794f5d8ead65b55089a6ec_Imagem_3d_7.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:50:58.205790', '2026-06-08 10:57:54'),
(78, 'Imagem 3d_6.jpeg', '/static/uploads/c688390a2abd4942a431be22c9b33f4d_Imagem_3d_6.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:51:11.403603', '2026-06-08 10:57:54'),
(79, 'Imagem 3d_5.jpeg', '/static/uploads/c2914239cda54e62a7b7af40a28e1afa_Imagem_3d_5.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:51:24.581619', '2026-06-08 10:57:55'),
(80, 'Imagem 3d_4.jpeg', '/static/uploads/a52996ab7e3f437c80e9213aa00a8b3c_Imagem_3d_4.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:51:36.985280', '2026-06-08 10:57:55'),
(81, 'Imagem 3d_9.jpeg', '/static/uploads/a8d13cc31bf34fc3933115bcfde7fdbd_Imagem_3d_9.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:51:49.702397', '2026-06-08 10:58:32'),
(82, 'Imagem 3d_8.jpeg', '/static/uploads/07f0227cf849430385b39e2fad278f65_Imagem_3d_8.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:52:02.616628', '2026-06-08 10:58:33'),
(83, 'Imagem 3d_16.jpeg', '/static/uploads/1b928e534060400e8cc19de68a966696_Imagem_3d_16.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:52:14.931027', '2026-06-08 10:58:33'),
(84, 'Imagem 3d_15.jpeg', '/static/uploads/042cfb7891514c5a85c8dfcd03ba984d_Imagem_3d_15.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:52:27.319423', '2026-06-08 10:58:33'),
(85, 'Imagem 3d_14.jpeg', '/static/uploads/7f026fc96501459d9eba8119f06ecf89_Imagem_3d_14.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:52:39.876866', '2026-06-08 10:58:33'),
(86, 'Imagem 3d_13.jpeg', '/static/uploads/de2646a8ff8c48399df9855eedc261a9_Imagem_3d_13.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:52:54.832535', '2026-06-08 10:58:33'),
(87, 'Imagem 3d_12.jpeg', '/static/uploads/95c00d8099cb45009f1b3166fac51c92_Imagem_3d_12.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:53:07.422262', '2026-06-08 10:58:34'),
(88, 'Imagem 3d_11.jpeg', '/static/uploads/752a05e2c249472aaf61e1a365eee82a_Imagem_3d_11.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:53:20.888373', '2026-06-08 10:58:34'),
(89, 'Imagem 3d_10.jpeg', '/static/uploads/ff60e48b14bd4ed89f7dcf40cf5a360b_Imagem_3d_10.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:53:34.037016', '2026-06-08 10:58:34'),
(90, 'Imagem 3d_17.jpeg', '/static/uploads/60c6649149a346e7882993c427b5ea4a_Imagem_3d_17.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:53:46.390482', '2026-06-08 10:58:58'),
(91, 'Video Planta.mp4', '/static/uploads/ba2keb936xjb37yyga5h7a_Video_Planta.mp4', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:53:59.128552', '2026-06-08 20:37:02'),
(92, 'Imagem 3d_3.jpeg', '/static/uploads/mnrflk0ust8d7dukdtxxo_Imagem_3d_3.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T20:38:59.651121', '2026-06-08 20:38:23'),
(93, 'Imagem 3d_3.jpeg', '/static/uploads/p6ezsxns6xiaw52t3rwqoh_Imagem_3d_3.jpeg', 'instituto', 'raiz', 'arquivo', 71, 'Petrick Martins', 1, '2026-06-08T21:54:12.641336', '2026-06-08 20:45:20'),
(94, 'Portfolio Fight Community BrasíliaDF.pdf', '/static/uploads/x1s0wz9605r4byds3hbqx3_Portfolio_Fight_Community_BrasliaDF.pdf', 'instituto', 'raiz', 'arquivo', 25, 'Petrick Martins', 1, '2026-06-09T13:15:41.392862', '2026-06-08 21:11:45'),
(95, 'Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '/static/uploads/nf7ez4b1185kxv07gq9lr_Arrai_Solidrio_2026_-_Portflio_Vila_Planalto-1.pdf', 'instituto', 'raiz', 'arquivo', 18, 'Petrick Martins', 1, '2026-06-09T02:34:42.511980', '2026-06-08 21:24:47'),
(96, 'Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '/static/uploads/v9c8d6v2yeen9a9jfj89_Arrai_Solidrio_2026_-_Portflio_Vila_Planalto-1.pdf', 'instituto', 'raiz', 'arquivo', 18, 'Petrick Martins', 1, '2026-06-09T13:15:05.757237', '2026-06-09 02:35:24'),
(97, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-09T02:37:12.893495', '2026-06-09 02:36:53'),
(98, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:09:43'),
(99, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:04'),
(100, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:04'),
(101, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:08'),
(102, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:08'),
(103, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:13'),
(104, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:13'),
(105, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:17'),
(106, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:17'),
(107, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:10:21'),
(108, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-09T03:10:56.998059', '2026-06-09 03:10:38'),
(109, 'IBDTEC', 'https://ibdtec.ong.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 0, NULL, '2026-06-09 03:11:17'),
(110, 'EXPO FEIRASCO', 'https://expofeirasco.com.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-09T03:12:26.097709', '2026-06-09 03:12:02'),
(111, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-09T13:17:55.541018', '2026-06-09 13:17:19'),
(112, 'Logo Evento.jpeg', '/static/uploads/7r3x93lq6vr54w2vkr4h0k_Logo_Evento.jpeg', 'instituto', 'instituto', 'arquivo', NULL, 'Petrick Martins', 1, '2026-06-09 10:23:49', '2026-06-09 13:23:26'),
(113, 'Logo Evento.jpeg', '/static/uploads/jlbuloc0ejl6pgg9p56a_Logo_Evento.jpeg', 'instituto', 'instituto', 'arquivo', NULL, 'Petrick Martins', 1, '2026-06-09 10:33:00', '2026-06-09 13:32:51'),
(114, 'Evento Ciência e Tecnologia.pdf', '/static/uploads/gj2mzurkz2jhn4ofgm1856_Evento_Cincia_e_Tecnologia.pdf', 'instituto', 'raiz', 'arquivo', 19, 'JEFFERSON SOUSA', 1, '2026-06-09 10:40:19', '2026-06-09 13:37:53'),
(115, 'I Love Image', 'https://www.iloveimg.com/pt', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-17 07:54:07', '2026-06-09 13:42:32'),
(116, 'I Love PDF', 'https://www.ilovepdf.com/pt', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-17 07:54:17', '2026-06-09 13:44:47'),
(117, 'Gov Br', 'https://www.gov.br', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-17 07:54:28', '2026-06-09 13:45:10'),
(118, 'Chat GPT', 'https://chatgpt.com/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-17 07:54:38', '2026-06-09 13:45:55'),
(119, 'Gemini IA', 'https://gemini.google.com/app?hl=pt-BR', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-16 18:00:07', '2026-06-09 13:46:51'),
(120, 'Gemini IA', 'https://gemini.google.com/app?hl=pt-BR', 'sites_jp2', 'sites_jp2', 'link', NULL, 'JEFFERSON SOUSA', 1, '2026-06-09 10:53:15', '2026-06-09 13:46:59'),
(121, 'Projetos', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-09 21:29:39', '2026-06-10 00:12:59'),
(122, 'Projetos', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-10 00:30:10'),
(123, 'Documentos', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-10 00:30:25'),
(124, 'Certidões', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-10 00:30:49'),
(125, 'Fomento', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 0, NULL, '2026-06-10 00:31:02'),
(126, 'Logo JP2 Business.jpg', 'r2://jp2-painel-documentos/uploads/instituto/o1qi5a3wi9pag6ceis718l_Logo_JP2_Business.jpg', 'instituto', 'instituto', 'arquivo', NULL, 'Petrick Martins', 1, '2026-06-16 15:58:32', '2026-06-16 17:08:37'),
(127, 'Logo JP2 Business.jpg', 'r2://jp2-painel-documentos/uploads/instituto/1uziqlh0mrzjhax0ws0p7r_Logo_JP2_Business.jpg', 'instituto', 'raiz', 'arquivo', 123, 'Petrick Martins', 1, '2026-06-16 14:21:20', '2026-06-16 17:21:06'),
(128, 'Logo JP2 Business.jpg', 'r2://jp2-painel-documentos/uploads/instituto/wazasgmnnlq2hknurb7m58_Logo_JP2_Business.jpg', 'instituto', 'instituto', 'arquivo', NULL, 'Petrick Martins', 1, '2026-06-16 15:58:23', '2026-06-16 18:58:14'),
(129, 'PETRICK', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-16 15:59:00', '2026-06-16 18:58:50'),
(130, 'PETRICK', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-16 16:00:57', '2026-06-16 19:00:18'),
(131, 'PETRICK', NULL, 'instituto', 'raiz', 'pasta', NULL, 'Petrick Martins', 1, '2026-06-16 16:22:18', '2026-06-16 19:22:03'),
(132, 'Registro Civil', 'https://www.registrocivil.org.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-17 08:27:20', '2026-06-17 11:27:01'),
(133, 'gov.br', 'https://sso.acesso.gov.br/', 'sites_jp2', 'sites_jp2', 'link', NULL, 'Petrick Martins', 1, '2026-06-17 09:46:11', '2026-06-17 11:28:52'),
(134, 'Logo JP2 Business.jpg', 'r2://jp2-painel-documentos/uploads/instituto/68r5ho2b0h9ypc0whvqeic_Logo_JP2_Business.jpg', 'instituto', 'raiz', 'arquivo', 124, 'Petrick Martins', 1, '2026-06-17 09:07:36', '2026-06-17 12:07:24'),
(135, 'PETRICK', NULL, 'instituto', 'raiz', 'pasta', 124, 'Petrick Martins', 1, '2026-06-17 09:08:24', '2026-06-17 12:08:07'),
(136, 'PETRICK', NULL, 'instituto', 'raiz', 'pasta', 124, 'Petrick Martins', 1, '2026-06-17 09:13:05', '2026-06-17 12:10:31'),
(137, 'Logo JP2 Business.jpg', 'r2://jp2-painel-documentos/uploads/instituto/q66n16ynacdw42808sjxg_Logo_JP2_Business.jpg', 'instituto', 'raiz', 'arquivo', 124, 'Petrick Martins', 1, '2026-06-17 09:12:50', '2026-06-17 12:11:52'),
(138, '1.png', 'r2://jp2-painel-documentos/uploads/instituto/kz4mva45509y8uflpvei5e_1.png', 'instituto', 'instituto', 'arquivo', NULL, 'Petrick Martins', 1, '2026-06-17 10:03:39', '2026-06-17 13:02:53');

-- --------------------------------------------------------

--
-- Estrutura para tabela `calculo_mensal`
--

CREATE TABLE `calculo_mensal` (
  `id` int(11) NOT NULL,
  `investimento_id` int(11) DEFAULT NULL,
  `mes_referencia` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `valor_inicial` decimal(15,2) DEFAULT NULL,
  `juros_aplicados` decimal(15,2) DEFAULT NULL,
  `valor_juros` decimal(15,2) DEFAULT NULL,
  `valor_final` decimal(15,2) DEFAULT NULL,
  `pagamento_realizado` decimal(15,2) DEFAULT '0.00',
  `saldo_devedor` decimal(15,2) DEFAULT NULL,
  `data_registro` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `contatos_telefonicos`
--

CREATE TABLE `contatos_telefonicos` (
  `id` int(11) NOT NULL,
  `nome` varchar(160) COLLATE utf8mb4_unicode_ci NOT NULL,
  `empresa` varchar(160) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cargo` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `telefone` varchar(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `whatsapp` varchar(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(160) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categoria` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'geral',
  `observacoes` text COLLATE utf8mb4_unicode_ci,
  `criado_por` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `contatos_telefonicos`
--

INSERT INTO `contatos_telefonicos` (`id`, `nome`, `empresa`, `cargo`, `telefone`, `whatsapp`, `email`, `categoria`, `observacoes`, `criado_por`, `criado_em`, `atualizado_em`) VALUES
(3, 'Petrick Martins', 'JP2 BUSINESS', 'DIRETOR', '62 985212173', '62 985212173', 'petrickmsilva@gmail.com', 'pessoal', '', 'Petrick Martins', '2026-06-17 17:02:46', '2026-06-17 17:02:46'),
(4, 'JEFFERSON JUSTINO', 'JP2 BUSINESS', 'DIRETOR', '+55 62 9688-0762', '+55 62 9688-0762', 'jjustino.sousa@gmail.com', 'pessoal', '', 'Petrick Martins', '2026-06-17 17:05:19', '2026-06-17 17:05:19');

-- --------------------------------------------------------

--
-- Estrutura para tabela `empresas`
--

CREATE TABLE `empresas` (
  `id` int(11) NOT NULL,
  `nome` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `cnpj` varchar(20) COLLATE utf8_unicode_ci DEFAULT NULL,
  `ramo_atividade` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Despejando dados para a tabela `empresas`
--

INSERT INTO `empresas` (`id`, `nome`, `cnpj`, `ramo_atividade`) VALUES
(1, ' Brobond Wear Ltda', '52.426.369/0001-64', 'Vestuário'),
(11, 'IBDTEC-INSTITUTO BRASILEIRO DE DESENVOLVIMENTO E TECNOLOGIA', '20.506.185/0001-18', 'INSTITUTO SOCIAL E EVENTOS'),
(12, 'VITALAB/NUTRALIS', '63.822.242/0001-80', 'MEDICAÇÃO/SAÚDE/BEM ESTAR');

-- --------------------------------------------------------

--
-- Estrutura para tabela `financeiro_emprestimos`
--

CREATE TABLE `financeiro_emprestimos` (
  `id` int(11) NOT NULL,
  `entidade` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `valor_original` decimal(15,2) DEFAULT NULL,
  `saldo_devedor` decimal(15,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Despejando dados para a tabela `financeiro_emprestimos`
--

INSERT INTO `financeiro_emprestimos` (`id`, `entidade`, `valor_original`, `saldo_devedor`) VALUES
(1, 'Desconhecido', 0.00, NULL),
(2, 'Desconhecido', 0.00, NULL),
(3, 'Desconhecido', 0.00, NULL),
(4, 'Desconhecido', 0.00, NULL),
(5, 'Desconhecido', 0.00, NULL),
(6, 'Desconhecido', 0.00, NULL),
(7, 'Desconhecido', 0.00, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `investimentos`
--

CREATE TABLE `investimentos` (
  `id` int(11) NOT NULL,
  `empresa_id` int(11) DEFAULT NULL,
  `nome_investidor` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `tipo_operacao` varchar(50) COLLATE utf8_unicode_ci DEFAULT NULL,
  `valor_inicial` decimal(15,2) DEFAULT NULL,
  `data_inicio` date DEFAULT NULL,
  `juros_mensais` decimal(5,4) DEFAULT NULL,
  `descricao` text COLLATE utf8_unicode_ci,
  `captador` varchar(255) COLLATE utf8_unicode_ci DEFAULT NULL,
  `tipo_recurso` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `finalidade` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `data_pgto` date DEFAULT NULL,
  `observacoes` text COLLATE utf8_unicode_ci,
  `valor_juros_day` decimal(15,2) DEFAULT NULL,
  `valor_divida_day` decimal(15,2) DEFAULT NULL,
  `pgto_day` decimal(15,2) DEFAULT NULL,
  `valor_divida_futuro` decimal(15,2) DEFAULT NULL,
  `importacao_origem` varchar(80) COLLATE utf8_unicode_ci DEFAULT NULL,
  `importacao_id` varchar(80) COLLATE utf8_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `logs_auditoria`
--

CREATE TABLE `logs_auditoria` (
  `id` int(11) NOT NULL,
  `usuario` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
  `acao` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `ip_origem` varchar(50) COLLATE utf8_unicode_ci NOT NULL,
  `data_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Despejando dados para a tabela `logs_auditoria`
--

INSERT INTO `logs_auditoria` (`id`, `usuario`, `acao`, `ip_origem`, `data_registro`) VALUES
(1, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.69.138.179, 10.28.44.1', '2026-06-05 19:33:12'),
(2, 'Petrick Martins', 'Cadastrou um novo usuário no painel: petrick', '177.223.35.230, 172.69.138.179, 10.28.44.1', '2026-06-05 19:33:40'),
(3, 'Petrick Martins', 'Criou a pasta: Projetos no bloco instituto', '177.223.35.230, 172.69.138.179, 10.28.44.1', '2026-06-05 19:34:02'),
(4, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-05 19:34:42'),
(5, 'Petrick Martins', 'Criou a pasta: Documentos no bloco instituto', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:40:18'),
(6, 'Petrick Martins', 'Criou a pasta: Certidões no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:40:28'),
(7, 'Petrick Martins', 'Criou a pasta: Fomento no bloco instituto', '177.223.35.230, 172.71.235.109, 10.31.144.132', '2026-06-05 19:40:47'),
(8, 'Petrick Martins', 'Criou a pasta: Empresa no bloco jp2_business', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:41:00'),
(9, 'Petrick Martins', 'Criou a pasta: Financeiro no bloco jp2_business', '177.223.35.230, 172.71.146.15, 10.31.144.132', '2026-06-05 19:41:11'),
(10, 'Petrick Martins', 'Criou a pasta: Arquivos no bloco jp2_business', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:41:25'),
(11, 'Petrick Martins', 'Criou a pasta: Administrativo no bloco jp2_business', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:41:38'),
(12, 'Petrick Martins', 'Criou a pasta: Arraia Solidário no bloco instituto', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:42:24'),
(13, 'Petrick Martins', 'Criou a pasta: Ciência e Tecnologia no bloco instituto', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:42:38'),
(14, 'Petrick Martins', 'Criou a pasta: Cinema Céu Aberto no bloco instituto', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 19:42:48'),
(15, 'Petrick Martins', 'Criou a pasta: Cinema de Rua no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:42:59'),
(16, 'Petrick Martins', 'Criou a pasta: Comunidade Festa Integração Escolas no bloco instituto', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 19:43:14'),
(17, 'Petrick Martins', 'Criou a pasta: Corrida de Verão no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:43:31'),
(18, 'Petrick Martins', 'Criou a pasta: Corrida Passos do Bem no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:43:45'),
(19, 'Petrick Martins', 'Criou a pasta: Luta Artes Marciais no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:43:57'),
(20, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 19:44:11'),
(21, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:44:30'),
(22, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:44:48'),
(23, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:45:06'),
(24, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 19:45:26'),
(25, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:45:54'),
(26, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:46:17'),
(27, 'Petrick Martins', 'Criou a pasta: Portifólio no bloco instituto', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 19:46:39'),
(28, 'Petrick Martins', 'Criou a pasta: Planta 3D no bloco instituto', '177.223.35.230, 172.71.146.15, 10.31.144.132', '2026-06-05 19:52:11'),
(29, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Planta 3D (ID: 32)', '177.223.35.230, 172.71.235.110, 10.28.44.1', '2026-06-05 19:53:00'),
(30, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: BrandBook_Imagens_Material_Corrida_do_Ver__o.png (ID: 31)', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 19:53:14'),
(31, 'Petrick Martins', 'Criou a pasta: Planta 3D no bloco instituto', '177.223.35.230, 172.71.146.15, 10.31.144.132', '2026-06-05 19:53:38'),
(32, 'Petrick Martins', 'Adicionou um compromisso na agenda: REUNIAO COM PEIXOTO', '177.223.35.230, 172.71.146.15, 10.31.144.132', '2026-06-05 19:55:10'),
(33, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 1', '177.223.35.230, 172.71.235.110, 10.29.13.1', '2026-06-05 19:55:28'),
(34, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 20:07:08'),
(35, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 20:07:28'),
(36, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.20, 10.28.44.1', '2026-06-05 20:10:31'),
(37, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.146.14, 10.28.44.1', '2026-06-05 20:20:07'),
(38, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-05 20:20:48'),
(39, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br)', '177.223.35.230, 172.71.146.15, 10.28.44.1', '2026-06-05 20:21:08'),
(40, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.238.129, 10.29.13.1', '2026-06-05 20:29:41'),
(41, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br)', '177.223.35.230, 172.71.150.20, 10.28.44.1', '2026-06-05 20:29:58'),
(42, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-05 20:33:09'),
(43, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:50:46'),
(44, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 40)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:51:09'),
(45, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 39)', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 20:51:24'),
(46, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 38)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:51:38'),
(47, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 37)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:51:53'),
(48, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 36)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:52:08'),
(49, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 2)', '177.223.35.230, 172.71.146.15, 10.28.44.1', '2026-06-05 20:52:22'),
(50, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 20:52:38'),
(51, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 41)', '177.223.35.230, 172.71.150.21, 10.26.177.2', '2026-06-05 20:52:54'),
(52, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-05 21:03:43'),
(53, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 42)', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-05 21:17:08'),
(54, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.146.14, 10.29.13.1', '2026-06-05 21:17:19'),
(55, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.22.10.162, 10.29.13.1', '2026-06-05 21:26:31'),
(56, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-05 21:26:49'),
(57, 'Petrick Martins', 'Realizou logout no sistema', '177.223.35.230, 172.71.146.15, 10.28.44.1', '2026-06-05 21:47:57'),
(58, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.238.128, 10.26.177.2', '2026-06-05 21:48:22'),
(59, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 43)', '177.223.35.230, 172.71.146.15, 10.28.44.1', '2026-06-05 21:48:40'),
(60, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 44)', '177.223.35.230, 172.71.146.15, 10.29.13.1', '2026-06-05 21:49:05'),
(61, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Registro Civil (ID: 44)', '177.223.35.230, 172.71.238.128, 10.26.177.2', '2026-06-05 21:49:05'),
(62, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.69.39.49, 10.31.144.132', '2026-06-05 22:04:46'),
(63, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.150.20, 10.26.177.2', '2026-06-05 22:05:07'),
(64, 'Petrick Martins', 'Adicionou um compromisso na agenda: REUNIAO COM PEIXOTO', '177.223.35.230, 172.71.146.15, 10.26.177.2', '2026-06-05 22:05:41'),
(65, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 2', '177.223.35.230, 172.71.150.20, 10.26.177.2', '2026-06-05 22:06:00'),
(66, 'Petrick Martins', 'Cadastrou um novo usuário no painel: jefferson', '177.223.35.230, 172.71.150.105, 10.28.44.1', '2026-06-05 22:07:23'),
(67, 'Petrick Martins', 'Realizou logout no sistema', '177.223.35.230, 172.71.150.104, 10.29.13.1', '2026-06-05 22:07:35'),
(68, 'JEFFERSON SOUSA', 'Realizou login no sistema', '177.223.35.230, 172.69.138.178, 10.26.177.2', '2026-06-05 22:08:38'),
(69, 'JEFFERSON SOUSA', 'Realizou login no sistema', '177.223.35.230, 172.71.146.15, 10.31.144.132', '2026-06-05 22:08:52'),
(70, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-06 12:51:28'),
(71, 'Petrick Martins', 'Cadastrou um novo usuário no painel: peixoto', '177.223.35.230, 172.71.235.110, 10.29.13.1', '2026-06-06 12:52:58'),
(72, 'Petrick Martins', 'Renomeou o(a) pasta \'Projetos\' para \'PROJETOS\' (ID: 1)', '177.223.35.230, 172.71.146.201, 10.31.144.132', '2026-06-06 14:28:47'),
(73, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0064.jpg (ID: 66)', '177.223.35.230, 172.71.151.30, 10.28.44.1', '2026-06-06 14:35:43'),
(74, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0064.jpg (ID: 67)', '177.223.35.230, 172.71.146.201, 10.31.144.132', '2026-06-06 14:42:23'),
(75, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0064.jpg (ID: 67)', '177.223.35.230, 172.71.151.30, 10.31.144.132', '2026-06-06 14:42:26'),
(76, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0063.jpg (ID: 68)', '177.223.35.230, 172.71.146.201, 10.31.144.132', '2026-06-06 14:42:40'),
(77, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0062.jpg (ID: 69)', '177.223.35.230, 172.71.151.30, 10.28.44.1', '2026-06-06 14:42:54'),
(78, 'Petrick Martins', 'Realizou login via mestre temporário', '179.249.64.112, 172.71.151.29, 10.31.144.132', '2026-06-06 15:17:41'),
(79, 'JEFFERSON SOUSA', 'Realizou login no sistema', '143.137.178.81, 104.23.254.166, 10.28.44.1', '2026-06-06 21:45:28'),
(80, 'JEFFERSON SOUSA', 'Realizou login no sistema', '143.137.178.81, 104.23.254.166, 10.28.44.1', '2026-06-06 21:45:29'),
(81, 'JEFFERSON SOUSA', 'Realizou login no sistema', '143.137.178.81, 172.71.150.20, 10.28.44.1', '2026-06-06 21:46:27'),
(82, 'JEFFERSON SOUSA', 'Realizou login no sistema', '143.137.178.81, 172.71.150.20, 10.28.44.1', '2026-06-06 21:46:38'),
(83, 'JEFFERSON SOUSA', 'Fez download do arquivo: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '143.137.178.81, 172.71.150.20, 10.28.44.1', '2026-06-06 21:47:22'),
(84, 'JEFFERSON SOUSA', 'Fez download do arquivo: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '143.137.178.81, 172.71.150.20, 10.28.44.1', '2026-06-06 21:47:36'),
(85, 'JEFFERSON SOUSA', 'Fez download do arquivo: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf', '143.137.178.81, 172.71.146.15, 10.29.13.1', '2026-06-06 21:47:47'),
(86, 'Petrick Martins', 'Criou a pasta: LOGO E BUNNER LUTA no bloco instituto', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-08 10:44:45'),
(87, 'Petrick Martins', 'Renomeou o(a) pasta \'LOGO E BUNNER LUTA\' para \'Logo e Bunner Luta\' (ID: 70)', '177.223.35.230, 172.71.146.207, 10.28.44.1', '2026-06-08 10:45:17'),
(88, 'Petrick Martins', 'Criou a pasta: Planta 3D Luta no bloco instituto', '177.223.35.230, 172.71.146.207, 10.28.44.1', '2026-06-08 10:46:02'),
(89, 'Petrick Martins', 'Fez download do arquivo: Logo Evento.jpeg', '177.223.35.230, 172.71.150.20, 10.29.137.132', '2026-06-08 12:19:48'),
(90, 'Petrick Martins', 'Fez download do arquivo: Logo Evento.jpeg', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-08 12:19:58'),
(91, 'Petrick Martins', 'Fez download do arquivo: Imagem 3d_1.jpeg', '177.223.35.230, 172.71.150.20, 10.28.44.1', '2026-06-08 15:47:08'),
(92, 'Petrick Martins', 'Fez download do arquivo: Imagem 3d_3.jpeg', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-08 15:47:59'),
(93, 'Petrick Martins', 'Realizou logout no sistema', '177.223.35.230, 172.71.146.206, 10.29.13.1', '2026-06-08 16:14:18'),
(94, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.22.10.162, 10.28.44.1', '2026-06-08 16:14:26'),
(95, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.69.114.136, 10.31.144.132', '2026-06-08 17:37:05'),
(96, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-08 17:44:04'),
(97, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.22.10.162, 10.31.144.132', '2026-06-08 18:02:37'),
(98, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.69.138.179, 10.29.13.1', '2026-06-08 18:59:16'),
(99, 'Petrick Martins', 'Renomeou o(a) pasta \'PROJETOS\' para \'Projetos\' (ID: 1)', '177.223.35.230, 172.71.150.21, 10.29.137.132', '2026-06-08 19:53:14'),
(100, 'Petrick Martins', 'Acessou arquivo via painel: Video Planta.mp4 (Download=False)', '177.223.35.230, 172.71.151.29, 10.29.13.1', '2026-06-08 20:37:19'),
(101, 'Petrick Martins', 'Acessou arquivo via painel: Video Planta.mp4 (Download=True)', '177.223.35.230, 172.71.151.29, 10.29.13.1', '2026-06-08 20:37:27'),
(102, 'Petrick Martins', 'Acessou arquivo via painel: Imagem 3d_3.jpeg (Download=False)', '177.223.35.230, 172.71.146.207, 10.29.13.1', '2026-06-08 20:38:40'),
(103, 'Petrick Martins', 'Acessou arquivo via painel: Imagem 3d_3.jpeg (Download=True)', '177.223.35.230, 172.71.151.29, 10.29.137.132', '2026-06-08 20:38:48'),
(104, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_3.jpeg (ID: 92)', '177.223.35.230, 172.71.147.158, 10.29.13.1', '2026-06-08 20:39:01'),
(105, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_3.jpeg (ID: 74)', '177.223.35.230, 104.22.10.162, 10.29.137.132', '2026-06-08 20:44:30'),
(106, 'Petrick Martins', 'Acessou arquivo via painel: Imagem 3d_3.jpeg (Download=False)', '177.223.35.230, 104.22.10.162, 10.29.137.132', '2026-06-08 20:45:31'),
(107, 'Petrick Martins', 'Acessou o arquivo: Portfolio Fight Community BrasíliaDF.pdf (Download=False)', '177.223.35.230, 172.71.150.21, 10.29.137.132', '2026-06-08 21:11:55'),
(108, 'Petrick Martins', 'Acessou o arquivo: Portfolio Fight Community BrasíliaDF.pdf (Download=True)', '177.223.35.230, 172.71.150.20, 10.28.44.1', '2026-06-08 21:12:15'),
(109, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf (ID: 26)', '177.223.35.230, 172.69.114.135, 10.31.144.132', '2026-06-08 21:23:26'),
(110, 'Petrick Martins', 'Acessou o arquivo: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf (Download=False)', '177.223.35.230, 172.71.150.228, 10.29.137.132', '2026-06-08 21:25:00'),
(111, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Evento Ciencia e Tecnologia.pdf (ID: 27)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:25:41'),
(112, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Cinema à Céu Aberto Lago Paranoá_2.0.pdf (ID: 28)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:26:11'),
(113, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: CineMovie Project_2.0.pdf (ID: 29)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:26:40'),
(114, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Comunidade em Festa.pdf (ID: 30)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:27:10'),
(115, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: BrandBook_Imagens_Material_Corrida_do_Ver__o.png (ID: 34)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:27:37'),
(116, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: 01 Planta 3d.zip (ID: 46)', '177.223.35.230, 172.71.150.228, 10.29.137.132', '2026-06-08 21:27:53'),
(117, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0047.jpg (ID: 47)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:28:07'),
(118, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0048.jpg (ID: 48)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:28:19'),
(119, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0049.jpg (ID: 49)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:28:34'),
(120, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0050.jpg (ID: 50)', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-08 21:28:51'),
(121, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0051.jpg (ID: 51)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:29:04'),
(122, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0052.jpg (ID: 52)', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-08 21:29:17'),
(123, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0053.jpg (ID: 53)', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-08 21:29:30'),
(124, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0054.jpg (ID: 54)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:29:41'),
(125, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0055.jpg (ID: 55)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:29:57'),
(126, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0056.jpg (ID: 56)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:30:09'),
(127, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0057.jpg (ID: 57)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:30:23'),
(128, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0058.jpg (ID: 58)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:30:35'),
(129, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0059.jpg (ID: 59)', '177.223.35.230, 172.71.150.228, 10.28.44.1', '2026-06-08 21:30:47'),
(130, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0060.jpg (ID: 60)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:31:00'),
(131, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0061.jpg (ID: 61)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:31:12'),
(132, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0062.jpg (ID: 62)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:31:24'),
(133, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0063.jpg (ID: 63)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:31:37'),
(134, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: IMG-20260429-WA0064.jpg (ID: 64)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:31:49'),
(135, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Circuito Corrida de Verão.pdf (ID: 35)', '177.223.35.230, 172.71.150.20, 10.29.13.1', '2026-06-08 21:32:11'),
(136, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Circuito Passos do Bem Run Series.pdf (ID: 65)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:32:47'),
(137, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Logo Evento.jpeg (ID: 72)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:33:18'),
(138, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Baner Fight Community.png (ID: 73)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:33:31'),
(139, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_2.jpeg (ID: 75)', '177.223.35.230, 172.69.138.179, 10.31.144.132', '2026-06-08 21:33:51'),
(140, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_1.jpeg (ID: 76)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:50:43'),
(141, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_1.jpeg (ID: 76)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:50:43'),
(142, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_1.jpeg (ID: 76)', '177.223.35.230, 172.71.150.229, 10.31.144.132', '2026-06-08 21:50:47'),
(143, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_7.jpeg (ID: 77)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:51:00'),
(144, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_6.jpeg (ID: 78)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:51:13'),
(145, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_5.jpeg (ID: 79)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:51:26'),
(146, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_4.jpeg (ID: 80)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:51:38'),
(147, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_9.jpeg (ID: 81)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:51:51'),
(148, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_8.jpeg (ID: 82)', '177.223.35.230, 172.71.150.229, 10.29.137.132', '2026-06-08 21:52:04'),
(149, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_16.jpeg (ID: 83)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:52:16'),
(150, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_15.jpeg (ID: 84)', '177.223.35.230, 172.71.150.229, 10.29.137.132', '2026-06-08 21:52:29'),
(151, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_14.jpeg (ID: 85)', '177.223.35.230, 172.71.150.229, 10.29.137.132', '2026-06-08 21:52:41'),
(152, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_13.jpeg (ID: 86)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:52:56'),
(153, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_12.jpeg (ID: 87)', '177.223.35.230, 172.71.150.229, 10.29.137.132', '2026-06-08 21:53:09'),
(154, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_11.jpeg (ID: 88)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:53:22'),
(155, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_10.jpeg (ID: 89)', '177.223.35.230, 172.69.138.178, 10.31.144.132', '2026-06-08 21:53:35'),
(156, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_17.jpeg (ID: 90)', '177.223.35.230, 172.71.150.229, 10.29.137.132', '2026-06-08 21:53:48'),
(157, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Video Planta.mp4 (ID: 91)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:54:01'),
(158, 'Petrick Martins', 'Enviou para a lixeira o item/pasta: Imagem 3d_3.jpeg (ID: 93)', '177.223.35.230, 172.69.138.178, 10.29.13.1', '2026-06-08 21:54:14'),
(159, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.235.109, 10.29.13.1', '2026-06-08 23:28:28'),
(160, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.228, 10.28.44.1', '2026-06-09 00:00:54'),
(161, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.29.137.132', '2026-06-09 00:27:35'),
(162, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-09 00:43:31'),
(163, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.22.10.83, 10.29.137.132', '2026-06-09 01:20:59'),
(164, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.23.254.221, 10.31.144.132', '2026-06-09 01:32:37'),
(165, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [95])', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-09 02:34:44'),
(166, 'Petrick Martins', 'Acessou o arquivo: Arraiá Solidário 2026 - Portfólio Vila Planalto-1.pdf (Download=False)', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-09 02:35:47'),
(167, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [45])', '177.223.35.230, 104.23.254.132, 10.31.144.132', '2026-06-09 02:36:35'),
(168, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-09 02:36:54'),
(169, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [97])', '177.223.35.230, 172.71.150.21, 10.31.144.132', '2026-06-09 02:37:14'),
(170, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.238.89, 10.29.13.1', '2026-06-09 03:09:45'),
(171, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-09 03:10:06'),
(172, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-09 03:10:06'),
(173, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.21, 10.28.44.1', '2026-06-09 03:10:10'),
(174, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.146.14, 10.31.144.132', '2026-06-09 03:10:10'),
(175, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.146.14, 10.31.144.132', '2026-06-09 03:10:14'),
(176, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.146.14, 10.31.144.132', '2026-06-09 03:10:15'),
(177, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.20, 10.29.13.1', '2026-06-09 03:10:19'),
(178, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.20, 10.28.44.1', '2026-06-09 03:10:19'),
(179, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.238.88, 10.29.13.1', '2026-06-09 03:10:23'),
(180, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.146.14, 10.31.144.132', '2026-06-09 03:10:40'),
(181, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [108])', '177.223.35.230, 172.71.146.201, 10.29.13.1', '2026-06-09 03:10:58'),
(182, 'Petrick Martins', 'Incluiu o site institucional: IBDTEC (https://ibdtec.ong.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-09 03:11:18'),
(183, 'Petrick Martins', 'Incluiu o site institucional: EXPO FEIRASCO (https://expofeirasco.com.br/)', '177.223.35.230, 172.71.150.20, 10.31.144.132', '2026-06-09 03:12:03'),
(184, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [110])', '177.223.35.230, 172.71.150.21, 10.29.13.1', '2026-06-09 03:12:28'),
(185, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.23.254.67, 10.28.44.1', '2026-06-09 12:01:41'),
(186, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.10.56, 10.31.144.132', '2026-06-09 12:13:18'),
(187, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.151.177, 10.29.130.129', '2026-06-09 12:32:41'),
(188, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [96])', '177.223.35.230, 172.69.114.52, 10.29.13.1', '2026-06-09 13:15:07'),
(189, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [94])', '177.223.35.230, 172.71.151.232, 10.28.44.1', '2026-06-09 13:15:43'),
(190, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.223.35.230, 172.71.234.232, 10.29.130.129', '2026-06-09 13:17:21'),
(191, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [111])', '177.223.35.230, 172.71.234.70, 10.31.144.132', '2026-06-09 13:17:54'),
(192, 'Petrick Martins', 'Enviou para a lixeira um lote de itens (IDs: [111])', '177.223.35.230, 172.71.234.71, 10.29.130.129', '2026-06-09 13:17:57'),
(193, 'Petrick Martins', 'Enviou para a lixeira IDs: 112', '177.223.35.230, 172.71.151.128, 10.29.13.1', '2026-06-09 13:23:51'),
(194, 'Petrick Martins', 'Enviou para a lixeira IDs: 113', '177.223.35.230, 172.71.10.148, 10.29.130.129', '2026-06-09 13:33:02'),
(195, 'JEFFERSON SOUSA', 'Realizou login no sistema', '177.223.35.230, 172.71.238.85, 10.28.44.1', '2026-06-09 13:35:25'),
(196, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 172.71.151.128, 10.31.144.132', '2026-06-09 13:39:27'),
(197, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 172.71.146.100, 10.31.144.132', '2026-06-09 13:39:32'),
(198, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 172.71.146.101, 10.28.44.1', '2026-06-09 13:39:32'),
(199, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 172.71.146.84, 10.29.130.129', '2026-06-09 13:39:36'),
(200, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 104.23.254.185, 10.29.130.129', '2026-06-09 13:39:40'),
(201, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=False)', '177.223.35.230, 104.23.254.184, 10.31.144.132', '2026-06-09 13:39:44'),
(202, 'JEFFERSON SOUSA', 'Acessou o arquivo: Evento Ciência e Tecnologia.pdf (Download=True)', '177.223.35.230, 172.71.146.84, 10.29.130.129', '2026-06-09 13:39:53'),
(203, 'JEFFERSON SOUSA', 'Enviou para a lixeira IDs: 114', '177.223.35.230, 172.69.138.196, 10.29.130.129', '2026-06-09 13:40:21'),
(204, 'JEFFERSON SOUSA', 'Incluiu o site institucional: I Love Image (https://www.iloveimg.com/pt)', '177.223.35.230, 172.71.146.208, 10.31.144.132', '2026-06-09 13:42:34'),
(205, 'JEFFERSON SOUSA', 'Incluiu o site institucional: I Love PDF (https://www.ilovepdf.com/pt)', '177.223.35.230, 172.69.138.197, 10.29.130.129', '2026-06-09 13:44:49'),
(206, 'JEFFERSON SOUSA', 'Incluiu o site institucional: Gov Br (https://www.gov.br)', '177.223.35.230, 172.71.151.178, 10.29.13.1', '2026-06-09 13:45:12'),
(207, 'JEFFERSON SOUSA', 'Incluiu o site institucional: Chat GPT (https://chatgpt.com/)', '177.223.35.230, 172.71.150.186, 10.29.13.1', '2026-06-09 13:45:56'),
(208, 'JEFFERSON SOUSA', 'Incluiu o site institucional: Gemini IA (https://gemini.google.com/app?hl=pt-BR)', '177.223.35.230, 172.71.151.178, 10.29.13.1', '2026-06-09 13:47:06'),
(209, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.147.159, 10.31.144.132', '2026-06-09 22:42:41'),
(210, 'Petrick Martins', 'Criou a pasta: Projetos no bloco instituto', '177.223.35.230, 172.71.150.224, 10.29.13.1', '2026-06-10 00:13:01'),
(211, 'Petrick Martins', 'Criou a pasta: Projetos no bloco instituto', '177.223.35.230, 172.71.150.224, 10.28.44.1', '2026-06-10 00:30:12'),
(212, 'Petrick Martins', 'Criou a pasta: Documentos no bloco instituto', '177.223.35.230, 172.68.19.144, 10.29.13.1', '2026-06-10 00:30:26'),
(213, 'Petrick Martins', 'Criou a pasta: Certidões no bloco instituto', '177.223.35.230, 172.71.150.224, 10.28.44.1', '2026-06-10 00:30:51'),
(214, 'Petrick Martins', 'Criou a pasta: Fomento no bloco instituto', '177.223.35.230, 172.68.19.144, 10.29.13.1', '2026-06-10 00:31:04'),
(215, 'JEFFERSON SOUSA', 'Realizou login no sistema', '191.54.20.110, 172.69.11.202, 10.31.144.132', '2026-06-10 02:30:17'),
(216, 'JEFFERSON SOUSA', 'Realizou login no sistema', '191.54.20.110, 172.69.11.202, 10.31.144.132', '2026-06-10 02:30:18'),
(217, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.146.214, 10.29.13.1', '2026-06-10 18:50:55'),
(218, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.10.148, 10.29.180.2', '2026-06-10 19:39:24'),
(219, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.146.85, 10.29.180.2', '2026-06-10 19:46:51'),
(220, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 172.71.146.214, 10.29.180.2', '2026-06-10 21:50:15'),
(221, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.23.254.185, 10.28.44.1', '2026-06-10 22:26:43'),
(222, 'JEFFERSON SOUSA', 'Realizou login no sistema', '191.55.196.195, 104.22.10.180, 10.31.144.132', '2026-06-11 03:31:00'),
(223, 'JEFFERSON SOUSA', 'Realizou login no sistema', '191.55.196.195, 172.71.147.55, 10.29.13.1', '2026-06-11 03:31:01'),
(224, 'JEFFERSON SOUSA', 'Realizou login no sistema', '191.55.196.195, 172.71.147.55, 10.28.44.1', '2026-06-11 03:32:33'),
(225, 'Petrick Martins', 'Realizou login via mestre temporário', '177.223.35.230, 104.22.10.180, 10.29.13.1', '2026-06-11 16:32:04'),
(226, 'Petrick Martins', 'Realizou login via mestre temporário', '177.203.149.207, 172.71.147.159, 10.26.116.129', '2026-06-11 19:26:37'),
(227, 'Petrick Martins', 'Realizou logout no sistema', '177.203.149.207, 172.71.146.198, 10.29.180.2', '2026-06-11 19:30:29'),
(228, 'PETRICK MARTINS', 'Realizou login no sistema', '177.200.35.142, 172.71.146.198, 10.30.62.231', '2026-06-16 13:33:30'),
(229, 'PETRICK MARTINS', 'Removeu o usuÃ¡rio ID: 2 do sistema', '177.200.35.142, 172.71.146.198, 10.28.81.1', '2026-06-16 13:35:27'),
(230, 'PETRICK MARTINS', 'Removeu o usuÃ¡rio ID: 3 do sistema', '177.200.35.142, 172.71.146.198, 10.30.62.231', '2026-06-16 13:35:36'),
(231, 'PETRICK MARTINS', 'Removeu o usuÃ¡rio ID: 1 do sistema', '177.200.35.142, 172.71.146.198, 10.30.62.231', '2026-06-16 13:36:00'),
(232, 'PETRICK MARTINS', 'Cadastrou um novo usuÃ¡rio no painel: petrick', '177.200.35.142, 172.71.146.85, 10.30.62.231', '2026-06-16 13:36:15'),
(233, 'PETRICK MARTINS', 'Cadastrou um novo usuÃ¡rio no painel: jefferson', '177.200.35.142, 172.71.151.178, 10.31.98.132', '2026-06-16 13:36:52'),
(234, 'PETRICK MARTINS', 'Cadastrou um novo usuÃ¡rio no painel: peixoto', '177.200.35.142, 172.71.146.198, 10.30.62.231', '2026-06-16 13:37:17'),
(235, 'PETRICK MARTINS', 'Realizou logout no sistema', '177.200.35.142, 172.70.140.96, 10.25.23.4', '2026-06-16 13:38:24'),
(236, 'JEFFERSON SOUSA', 'Realizou login no sistema', '177.200.35.142, 172.71.146.198, 10.30.62.231', '2026-06-16 13:38:40'),
(237, 'JEFFERSON SOUSA', 'Realizou logout no sistema', '177.200.35.142, 172.70.140.96, 10.28.81.1', '2026-06-16 13:40:27'),
(238, 'Petrick Martins', 'Realizou login no sistema', '177.200.35.142, 172.70.140.96, 10.25.23.4', '2026-06-16 13:40:44'),
(239, 'Petrick Martins', 'Acessou o arquivo: Logo JP2 Business.jpg (Download=False)', '177.200.35.142, 172.71.146.85, 10.30.62.231', '2026-06-16 17:17:28'),
(240, 'Petrick Martins', 'Acessou o arquivo: Logo JP2 Business.jpg (Download=True)', '177.200.35.142, 172.71.146.85, 10.30.62.231', '2026-06-16 17:17:37'),
(241, 'Petrick Martins', 'Realizou login no sistema', '177.200.35.142, 172.71.146.84, 10.28.165.220', '2026-06-16 17:49:04'),
(242, 'Petrick Martins', 'Alterou perfil do usuario jefferson para admin', '177.200.35.142, 172.71.151.178, 10.25.23.4', '2026-06-16 18:08:29'),
(243, 'Petrick Martins', 'Alterou perfil do usuario peixoto para leitura', '177.200.35.142, 172.71.146.84, 10.28.165.220', '2026-06-16 18:08:57'),
(244, 'Petrick Martins', 'Alterou perfil do usuario peixoto para socio', '177.200.35.142, 172.71.146.84, 10.31.98.132', '2026-06-16 18:14:38'),
(245, 'Petrick Martins', 'Realizou logout no sistema', '177.200.35.142, 172.71.151.178, 10.30.62.231', '2026-06-16 18:17:00'),
(246, 'JEFFERSON SOUSA', 'Realizou login no sistema', '177.200.35.142, 172.71.151.178, 10.30.62.231', '2026-06-16 18:17:23'),
(247, 'JEFFERSON SOUSA', 'Realizou logout no sistema', '177.200.35.142, 172.71.146.85, 10.28.165.220', '2026-06-16 18:17:50'),
(248, 'PEIXOTO JR.', 'Realizou login no sistema', '177.200.35.142, 172.71.151.178, 10.30.62.231', '2026-06-16 18:18:09'),
(249, 'PEIXOTO JR.', 'Realizou logout no sistema', '177.200.35.142, 172.71.146.85, 10.28.165.220', '2026-06-16 18:19:00'),
(250, 'Petrick Martins', 'Realizou login no sistema', '177.200.35.142, 172.71.146.84, 10.30.62.231', '2026-06-16 18:19:11'),
(251, 'Petrick Martins', 'Alterou a senha do usuario jefferson', '177.200.35.142, 172.71.146.85, 10.28.165.220', '2026-06-16 18:45:22'),
(252, 'Petrick Martins', 'Alterou a senha do usuario petrick', '177.200.35.142, 172.71.146.84, 10.30.62.231', '2026-06-16 18:45:59'),
(253, 'Petrick Martins', 'Criou a pasta: PETRICK no bloco instituto', '177.200.35.142, 172.71.151.178, 10.25.23.4', '2026-06-16 18:58:51'),
(254, 'Petrick Martins', 'Criou a pasta: PETRICK no bloco instituto', '177.200.35.142, 172.71.151.178, 10.25.23.4', '2026-06-16 19:00:19'),
(255, 'Petrick Martins', 'Criou a pasta: PETRICK no bloco instituto', '177.200.35.142, 172.71.151.177, 10.25.23.4', '2026-06-16 19:22:05'),
(256, 'Petrick Martins', 'Adicionou um compromisso na agenda: REUNIAO COM PEIXOTO', '177.200.35.142, 172.71.151.177, 10.28.165.220', '2026-06-16 19:53:12'),
(257, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 1', '177.200.35.142, 172.71.146.85, 10.25.23.4', '2026-06-16 19:53:53'),
(258, 'Petrick Martins', 'Adicionou um compromisso na agenda: Expo Fashion Brasil', '177.200.35.142, 172.71.146.198, 10.28.165.220', '2026-06-16 19:55:22'),
(259, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 2', '177.200.35.142, 172.71.146.199, 10.30.62.231', '2026-06-16 19:55:53'),
(260, 'Petrick Martins', 'Adicionou um compromisso na agenda: REUNIAO COM PEIXOTO', '177.200.35.142, 172.71.150.175, 10.25.23.4', '2026-06-16 19:56:34'),
(261, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 3', '177.200.35.142, 172.71.147.163, 10.30.62.231', '2026-06-16 19:56:55'),
(262, 'Petrick Martins', 'Adicionou um compromisso na agenda: Expo Fashion Brasil', '177.200.35.142, 172.71.151.177, 10.28.165.220', '2026-06-16 19:57:43'),
(263, 'Petrick Martins', 'Apagou o compromisso da agenda ID: 4', '177.200.35.142, 172.71.151.177, 10.28.165.220', '2026-06-16 19:58:21'),
(264, 'Petrick Martins', 'Realizou login no sistema', '179.249.64.172, 172.71.147.164, 10.28.165.220', '2026-06-16 21:10:07'),
(265, 'Petrick Martins', 'Realizou login no sistema', '179.249.64.172, 172.71.151.178, 10.28.165.220', '2026-06-16 21:10:14'),
(266, 'Petrick Martins', 'Realizou login no sistema', '179.249.64.172, 172.71.150.114, 10.30.62.231', '2026-06-16 21:10:21'),
(267, 'Petrick Martins', 'Incluiu o site institucional: Registro Civil (https://www.registrocivil.org.br/)', '177.200.35.142, 172.71.147.163, 10.31.98.132', '2026-06-17 11:27:02'),
(268, 'Petrick Martins', 'Incluiu o site institucional: gov.br (https://sso.acesso.gov.br/)', '177.200.35.142, 172.71.147.164, 10.30.62.231', '2026-06-17 11:28:53'),
(269, 'Petrick Martins', 'Criou a pasta: PETRICK no bloco instituto', '177.200.35.142, 172.71.147.164, 10.31.81.129', '2026-06-17 12:08:08'),
(270, 'Petrick Martins', 'Criou a pasta: PETRICK no bloco instituto', '177.200.35.142, 172.71.151.177, 10.31.98.132', '2026-06-17 12:10:32'),
(271, 'Petrick Martins', 'Cadastrou contato telefonico: PETRICK MARTINS', '177.200.35.142, 172.71.146.85, 10.31.81.129', '2026-06-17 16:16:48'),
(272, 'Petrick Martins', 'Atualizou contato telefonico ID: 1', '177.200.35.142, 172.71.146.85, 10.31.98.132', '2026-06-17 16:20:53'),
(273, 'Petrick Martins', 'Removeu contato telefonico ID: 1', '177.200.35.142, 172.71.146.85, 10.31.98.132', '2026-06-17 16:21:07'),
(274, 'Petrick Martins', 'Cadastrou contato telefonico: Petrick Martins', '177.200.35.142, 104.23.254.184, 10.25.23.4', '2026-06-17 16:32:41'),
(275, 'Petrick Martins', 'Removeu contato telefonico ID: 2', '177.200.35.142, 172.71.238.84, 10.31.81.129', '2026-06-17 16:37:52'),
(276, 'Petrick Martins', 'Cadastrou contato telefonico: Petrick Martins', '177.200.35.142, 172.71.146.84, 10.30.62.231', '2026-06-17 17:02:47'),
(277, 'Petrick Martins', 'Cadastrou contato telefonico: JEFFERSON JUSTINO', '177.200.35.142, 172.71.146.85, 10.30.62.231', '2026-06-17 17:05:21');

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `usuario` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
  `senha` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `nome_exibicao` varchar(100) COLLATE utf8_unicode_ci DEFAULT NULL,
  `data_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `perfil` varchar(20) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'socio'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Despejando dados para a tabela `usuarios`
--

INSERT INTO `usuarios` (`id`, `usuario`, `senha`, `nome_exibicao`, `data_registro`, `perfil`) VALUES
(4, 'petrick', 'scrypt:32768:8:1$t65DEJ4CywHzRWeo$45ab87e2aa87d070aa5249e07d101cbc1bbc0748fedb18d77c7b1449b2e6f2250387ee3a223746b3c207ceda3df28745c50a1c03002092e253be5a9d550bf504', 'Petrick Martins', '2026-06-16 13:36:14', 'admin'),
(5, 'jefferson', 'scrypt:32768:8:1$Nk8cMKKWdZJig4on$0b0c36b60d322efbcc4087b1f258a388fb32136950028b9ba22f33ac8b72ed59f07faff8f1fd6c501586ead0dc442cbcd2fa5e7dca987d8b2b876315c4f6aa23', 'JEFFERSON SOUSA', '2026-06-16 13:36:50', 'admin'),
(6, 'peixoto', 'scrypt:32768:8:1$pkSFbwA2oH3nrgMn$4b29967c7dd7ec5c7251174cdd032e8d17f3d0804800ee0b1a9c829fccaacf314748d89d36f3e18cbd351d9baaeff26b88f56036d016e4e03dc119f183dd36da', 'PEIXOTO JR.', '2026-06-16 13:37:15', 'socio');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `agenda_eventos`
--
ALTER TABLE `agenda_eventos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_agenda_data_evento` (`data_evento`);

--
-- Índices de tabela `arquivos_painel`
--
ALTER TABLE `arquivos_painel`
  ADD PRIMARY KEY (`id`),
  ADD KEY `bloco` (`bloco`,`pasta_pai_id`),
  ADD KEY `idx_arquivos_listagem` (`bloco`(50),`pasta_pai_id`,`deletado`,`tipo`(20),`nome_original`(191)),
  ADD KEY `idx_arquivos_pasta_nome` (`bloco`(50),`nome_original`(191),`tipo`(20),`deletado`),
  ADD KEY `idx_arquivos_resumo` (`tipo`(20),`deletado`);

--
-- Índices de tabela `calculo_mensal`
--
ALTER TABLE `calculo_mensal`
  ADD PRIMARY KEY (`id`),
  ADD KEY `investimento_id` (`investimento_id`);

--
-- Índices de tabela `contatos_telefonicos`
--
ALTER TABLE `contatos_telefonicos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_contatos_busca` (`nome`(120),`empresa`(120),`categoria`),
  ADD KEY `idx_contatos_categoria` (`categoria`,`nome`(120));

--
-- Índices de tabela `empresas`
--
ALTER TABLE `empresas`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `financeiro_emprestimos`
--
ALTER TABLE `financeiro_emprestimos`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `investimentos`
--
ALTER TABLE `investimentos`
  ADD PRIMARY KEY (`id`);

--
-- Índices de tabela `logs_auditoria`
--
ALTER TABLE `logs_auditoria`
  ADD PRIMARY KEY (`id`),
  ADD KEY `data_registro` (`data_registro`),
  ADD KEY `idx_logs_data_registro` (`data_registro`);

--
-- Índices de tabela `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `usuario` (`usuario`),
  ADD KEY `idx_usuarios_usuario` (`usuario`(80));

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `agenda_eventos`
--
ALTER TABLE `agenda_eventos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `arquivos_painel`
--
ALTER TABLE `arquivos_painel`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=139;

--
-- AUTO_INCREMENT de tabela `calculo_mensal`
--
ALTER TABLE `calculo_mensal`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `contatos_telefonicos`
--
ALTER TABLE `contatos_telefonicos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `empresas`
--
ALTER TABLE `empresas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de tabela `financeiro_emprestimos`
--
ALTER TABLE `financeiro_emprestimos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de tabela `investimentos`
--
ALTER TABLE `investimentos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `logs_auditoria`
--
ALTER TABLE `logs_auditoria`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=278;

--
-- AUTO_INCREMENT de tabela `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `calculo_mensal`
--
ALTER TABLE `calculo_mensal`
  ADD CONSTRAINT `calculo_mensal_ibfk_1` FOREIGN KEY (`investimento_id`) REFERENCES `investimentos` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
