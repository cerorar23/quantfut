// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Portuguese (`pt`).
class AppLocalizationsPt extends AppLocalizations {
  AppLocalizationsPt([String locale = 'pt']) : super(locale);

  @override
  String get accessBody1 =>
      'Um modelo estatístico calcula as probabilidades. Uma probabilidade não é uma certeza.';

  @override
  String get accessBody2 =>
      'Todos os dias, os mais prováveis, com a taxa de acerto histórica real.';

  @override
  String get accessBody3 =>
      'Acompanhe o avanço de cada desafio e quanto falta para concluí-lo.';

  @override
  String get accessBody4 =>
      'Com a cota e a probabilidade conjunta, para você saber o que arrisca.';

  @override
  String get accessBody5 =>
      'Marque presença, complete ofertas e convide amigos para desbloquear prognósticos.';

  @override
  String get accessCardBody =>
      'Guarde seu progresso e suas moedas em todos os seus dispositivos.';

  @override
  String get accessCardTitle => 'Entre para continuar';

  @override
  String get accessConsent =>
      'Tenho pelo menos 18 anos e aceito os termos e a política de privacidade.';

  @override
  String get accessConsentNeeded => 'Marque a caixa para continuar.';

  @override
  String get accessConsentRequired =>
      'Marque a caixa para continuar com o Google.';

  @override
  String accessConsentRich(String terms, String privacy) {
    return 'Tenho 18 anos ou mais e aceito os $terms e a $privacy.';
  }

  @override
  String get accessContinueWithGoogle => 'Continuar com o Google';

  @override
  String get accessDisclaimer =>
      'Apenas para fins informativos e de entretenimento. Os prognósticos não garantem resultados.';

  @override
  String get accessDocumentOpenError => 'Não foi possível abrir o documento.';

  @override
  String get accessForgotLink => 'Recuperar senha anterior';

  @override
  String get accessForgotSent =>
      'Se a conta existir, você receberá instruções por e-mail.';

  @override
  String get accessGenericError =>
      'Não foi possível concluir o acesso. Tente novamente.';

  @override
  String get accessGoogleError =>
      'Não foi possível entrar com o Google. Tente novamente.';

  @override
  String get accessKicker1 => 'PROBABILIDADES REAIS';

  @override
  String get accessKicker2 => 'ALTA PROBABILIDADE';

  @override
  String get accessKicker3 => 'DESAFIO ESCADA';

  @override
  String get accessKicker4 => 'MÚLTIPLA';

  @override
  String get accessKicker5 => 'MOEDAS';

  @override
  String get accessLinkButton => 'Vincular minha conta';

  @override
  String get accessLinkEmail => 'E-mail da sua conta anterior';

  @override
  String get accessLinkIntro =>
      'Vincule sua conta anterior para manter seu saldo e acesso.';

  @override
  String get accessLinkPassword => 'Senha anterior';

  @override
  String get accessOtherAccount => 'Usar outra conta';

  @override
  String get accessPreparingDocs =>
      'Estamos preparando os documentos de acesso.';

  @override
  String get accessPrivacy => 'Política de privacidade';

  @override
  String get accessRetry => 'Tentar acessar novamente';

  @override
  String get accessTagline =>
      'Jogos, análises e histórico. Uma probabilidade não é uma certeza.';

  @override
  String get accessTerms => 'Termos de uso';

  @override
  String get accessTitle1 => 'Entenda cada partida com dados.';

  @override
  String get accessTitle2 => 'Prognósticos com a taxa de acerto à vista.';

  @override
  String get accessTitle3 => 'Suba degrau por degrau.';

  @override
  String get accessTitle4 => 'Um bilhete selado antes das partidas.';

  @override
  String get accessTitle5 => 'Ganhe moedas e desbloqueie.';

  @override
  String get adsCardTitle => 'Vídeos com recompensa';

  @override
  String get adsFootnote =>
      'As moedas são creditadas ao terminar o vídeo. Se fechar antes, você não recebe moedas.';

  @override
  String get adsLimitReached =>
      'Limite de hoje atingido. Volte depois das 00:00 UTC.';

  @override
  String get adsLoading => 'Carregando vídeo…';

  @override
  String get adsPending => 'Suas moedas chegarão em instantes.';

  @override
  String adsProgress(int used, int cap) {
    return 'Hoje: $used de $cap';
  }

  @override
  String get adsUnavailable =>
      'Não há vídeos disponíveis agora. Tente mais tarde.';

  @override
  String get adsVerifying => 'Verificando sua recompensa…';

  @override
  String adsWaitFor(String time) {
    return 'Próximo vídeo em $time';
  }

  @override
  String adsWatchCta(int coins) {
    return 'Ver vídeo · +$coins moedas';
  }

  @override
  String alertsAbsencesOf(String team) {
    return 'Desfalques de $team';
  }

  @override
  String get alertsAdvantage => 'Vantagem';

  @override
  String get alertsAdvantageEmpty => 'Sem vantagens registradas.';

  @override
  String alertsChecked(String when) {
    return 'Verificado $when';
  }

  @override
  String get alertsDisadvantage => 'Desvantagem';

  @override
  String get alertsDisadvantageEmpty => 'Sem desvantagens registradas.';

  @override
  String get alertsDoubt => 'Dúvida';

  @override
  String get alertsNoCheck =>
      'Ainda não há verificação de desfalques para esta partida. Se a liga não tem esse dado, isso não significa que não haja lesionados.';

  @override
  String get alertsNote =>
      'Os desfalques podem mudar até o início. A escalação oficial sai pouco antes da partida.';

  @override
  String get alertsOut => 'Indisponível';

  @override
  String get alertsReasonFoot => 'Lesão no tornozelo ou pé';

  @override
  String get alertsReasonIllness => 'Doença';

  @override
  String get alertsReasonInjury => 'Lesão';

  @override
  String get alertsReasonKnee => 'Lesão no joelho';

  @override
  String get alertsReasonKnock => 'Pancada';

  @override
  String get alertsReasonMuscle => 'Lesão muscular';

  @override
  String get alertsReasonSuspension => 'Suspensão';

  @override
  String get alertsReasonUnknown => 'Motivo não informado';

  @override
  String get alertsSource => 'Fonte: API-Football';

  @override
  String alertsSummary(int out, int doubt) {
    String _temp0 = intl.Intl.pluralLogic(
      out,
      locale: localeName,
      other: '$out desfalques',
      one: '1 desfalque',
    );
    String _temp1 = intl.Intl.pluralLogic(
      doubt,
      locale: localeName,
      other: '$doubt dúvidas',
      one: '1 dúvida',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get alertsSuspended => 'Suspenso';

  @override
  String get apiGoogleNotVerified =>
      'O Google não conseguiu verificar o acesso.';

  @override
  String get apiInvalidResponse => 'Resposta inválida do servidor.';

  @override
  String get apiInvalidSession => 'Sessão inválida.';

  @override
  String apiLoadFailed(int status) {
    return 'Não foi possível carregar as informações (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'Não foi possível conectar. Verifique sua conexão e tente novamente.';

  @override
  String get apiSessionExpired => 'Inicie sessão novamente.';

  @override
  String get apiSignInWithGoogle => 'Inicie sessão com o Google.';

  @override
  String get artAnalyzeEach => 'ANALISE CADA SELEÇÃO';

  @override
  String get artCorners => 'ESCANTEIOS';

  @override
  String get artFootball => 'FUTEBOL';

  @override
  String get artForm => 'FORMA';

  @override
  String get artGoals => 'GOLS';

  @override
  String get artHeadToHead => 'CONFRONTO DIRETO';

  @override
  String get artHeading0 => 'FUTEBOL + NBA';

  @override
  String get artHeading1 => 'O CONTEXTO IMPORTA';

  @override
  String get artHeading2 => 'EXPLORE OS MERCADOS';

  @override
  String get artHeading3 => 'HISTÓRICO À VISTA';

  @override
  String get artHeading4 => 'DADOS + SEU CRITÉRIO';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'ESTATÍSTICAS';

  @override
  String get artTagline => 'ANALISE. COMPARE. EXPLORE.';

  @override
  String get artTransparency => 'TRANSPARÊNCIA';

  @override
  String get bannerAwaiting =>
      'JOGO DISPUTADO · aguardando o resultado oficial';

  @override
  String get bannerLive =>
      'JOGO EM ANDAMENTO · prognóstico selado antes do início';

  @override
  String bannerLost(String score) {
    return 'ERROU$score · prognóstico selado antes do início';
  }

  @override
  String bannerWon(String score) {
    return 'ACERTOU$score · prognóstico selado antes do início';
  }

  @override
  String get calendarEmpty => 'Não há confrontos para estes filtros.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count confrontos',
      one: '$count confronto',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Escolher data';

  @override
  String get calendarSearchHint => 'Busque equipes ou ligas';

  @override
  String get calendarTitle => 'Calendário · horário local';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted casos',
      one: '$formatted caso',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'Todos';

  @override
  String get commonAway => 'Visitante';

  @override
  String get commonCancel => 'Cancelar';

  @override
  String get commonClose => 'Fechar';

  @override
  String get commonConfirm => 'Confirmar';

  @override
  String get commonConnecting => 'Conectando…';

  @override
  String get commonDraw => 'Empate';

  @override
  String get commonHome => 'Mandante';

  @override
  String get commonRefresh => 'Atualizar';

  @override
  String get commonRetry => 'Tentar novamente';

  @override
  String get commonSeeVip => 'Ver acesso VIP';

  @override
  String get commonToday => 'Hoje';

  @override
  String get commonYesterday => 'Ontem';

  @override
  String countdownDays(int days, String time) {
    return '${days}d $time';
  }

  @override
  String detailChecked(String date) {
    return 'Verificado: $date';
  }

  @override
  String get detailFormationPending => 'Formação pendente';

  @override
  String get detailH2hTitle => 'Histórico direto (H2H)';

  @override
  String get detailInjuries => 'Desfalques informados';

  @override
  String get detailLineups => 'Escalações';

  @override
  String get detailLineupsPending => 'Escalações ainda não confirmadas.';

  @override
  String get detailNoFeatured =>
      'Nenhum prognóstico deste jogo entra no destaque (odds de 1,20 a 1,60 e probabilidade de 74% a 85%). Os abertos estão na lista abaixo.';

  @override
  String get detailNoH2h => 'Não há confrontos registrados para este jogo.';

  @override
  String get detailNoInjuries => 'Sem desfalques no relatório disponível.';

  @override
  String get detailNoInjuriesCheck =>
      'Não há verificação de desfalques disponível.';

  @override
  String get detailNoPicks => 'Não há prognósticos publicados para este jogo.';

  @override
  String get detailNoSealedModel =>
      'Não há prognóstico selado para este jogo. Abaixo estão as estimativas do modelo.';

  @override
  String get detailNoSealedModelVip =>
      'Não há prognóstico selado para este jogo. Abaixo estão as estimativas do modelo, com VIP.';

  @override
  String get detailNoStarters => 'Sem titulares confirmados.';

  @override
  String get detailReferee => 'Árbitro';

  @override
  String get detailRefereePending => 'Árbitro a confirmar.';

  @override
  String get detailTabAlerts => 'Alertas';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Prognósticos';

  @override
  String get detailTabStats => 'Análise';

  @override
  String get detailVipPickNotice => 'Este jogo tem um prognóstico VIP';

  @override
  String get dictAwayDefault => 'o visitante';

  @override
  String get dictHomeDefault => 'o mandante';

  @override
  String dictOddsAbove(String fair) {
    return 'A odd publicada supera a odd justa ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'A odd publicada fica abaixo da odd justa ($fair); o atrativo está na probabilidade, não no preço.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick com probabilidade calculada de $percent.';
  }

  @override
  String get dictPickDefault => 'O prognóstico';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'As odds do mercado sem margem implicam $total gols esperados ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'Uma probabilidade não é uma certeza. Decida com informação e jogue com responsabilidade.';

  @override
  String get factsAbsences => 'Desfalques';

  @override
  String get factsDrew => 'Empatou';

  @override
  String get factsHideLineup => 'Ocultar os onze';

  @override
  String factsInCompetition(String competition) {
    return 'Em $competition';
  }

  @override
  String get factsLastLineup => 'Última escalação conhecida';

  @override
  String get factsLastMatch => 'Última partida';

  @override
  String factsLineupMeta(String rival, String date) {
    return 'contra $rival · $date';
  }

  @override
  String get factsLineupNote =>
      'É a escalação dessa partida, não uma previsão da de hoje.';

  @override
  String get factsLost => 'Perdeu';

  @override
  String get factsNoLineup => 'Ainda não há escalação salva.';

  @override
  String get factsNoResult => 'Sem partidas anteriores registradas.';

  @override
  String get factsSeeAlerts => 'Ver alertas';

  @override
  String get factsShowLineup => 'Ver os onze';

  @override
  String get factsTitle => 'Dados da partida';

  @override
  String factsVs(String score, String rival) {
    return '$score contra $rival';
  }

  @override
  String get factsWon => 'Ganhou';

  @override
  String get famCardsSubtitle =>
      'Linhas de menos cartões com respaldo histórico';

  @override
  String get famCardsTitle => 'Cartões';

  @override
  String get famCornersSubtitle =>
      'Mais e menos escanteios da partida completa';

  @override
  String get famCornersTeamSubtitle =>
      'Mandante e visitante, cada um com sua linha';

  @override
  String get famCornersTeamTitle => 'Escanteios por equipe';

  @override
  String get famCornersTitle => 'Total de escanteios';

  @override
  String get famDoubleChanceSubtitle =>
      'Dois resultados possíveis em uma seleção';

  @override
  String get famDoubleChanceTitle => 'Dupla chance';

  @override
  String get famGoalsSubtitle => 'Totais com linhas avaliadas historicamente';

  @override
  String get famGoalsTitle => 'Gols da partida';

  @override
  String get famHandicapSubtitle => 'Linhas de proteção e empate com devolução';

  @override
  String get famHandicapTitle => 'Handicap asiático';

  @override
  String get famNbaSubtitle =>
      'Avaliação exploratória · pendente de confirmação';

  @override
  String get famNbaTeamTitle => 'NBA · Pontos da equipe';

  @override
  String get famNbaTotalTitle => 'NBA · Total da partida';

  @override
  String get famNbaWinnerTitle => 'NBA · Vencedor';

  @override
  String get famTeamGoalsSubtitle =>
      'Pelo menos um gol do mandante ou do visitante';

  @override
  String get famTeamGoalsTitle => 'Uma equipe marca';

  @override
  String get famWinnerSubtitle => 'Resultado 1X2 de alta probabilidade';

  @override
  String get famWinnerTitle => 'Vencedor da partida';

  @override
  String get featAgenda => 'Agenda temporariamente indisponível';

  @override
  String get featBalance => 'Acompanhamento em preparação';

  @override
  String get featCommunity => 'Comunidade em preparação';

  @override
  String get featLanguages => 'Traduções em preparação';

  @override
  String get featMatchData => 'Dados da partida temporariamente indisponíveis';

  @override
  String get featMeasurement => 'Medição em preparação';

  @override
  String get featNba => 'Modelo NBA em treinamento';

  @override
  String get featNotifications => 'Notificações em preparação';

  @override
  String get featPurchases => 'Compras em preparação';

  @override
  String get featStats => 'Estatísticas temporariamente indisponíveis';

  @override
  String get featVip => 'Acesso VIP temporariamente indisponível';

  @override
  String get featureTraining => 'Modelo em treinamento';

  @override
  String get fixtureFinished => 'FINALIZADO';

  @override
  String get fixtureLive => 'AO VIVO';

  @override
  String get fixtureLocalTime => 'HORA LOCAL';

  @override
  String get fixtureStartsIn => 'COMEÇA EM';

  @override
  String get fixtureTbd => 'A CONFIRMAR';

  @override
  String get forecastCanFail =>
      'Um prognóstico pode falhar; a probabilidade não garante o resultado.';

  @override
  String get forecastFeatured => 'DESTAQUE';

  @override
  String get forecastFree => 'GRATUITO';

  @override
  String get forecastHalfTime => 'INTERVALO';

  @override
  String get forecastInPlay => 'EM JOGO';

  @override
  String get forecastLiveScore => 'Placar ao vivo';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Placar ao vivo · atualizado há $minutes min';
  }

  @override
  String get forecastMarketNote =>
      'Probabilidades calculadas com as odds do mercado sem margem: esta liga não tem modelo próprio.';

  @override
  String get forecastOddsAtPublish => 'Odd na publicação';

  @override
  String forecastProbCalc(String percent) {
    return '$percent prob. calculada';
  }

  @override
  String get forecastSeeStats => 'Ver estatísticas do jogo';

  @override
  String get forecastSourceMarket => 'ODDS DO MERCADO';

  @override
  String get forecastSourceModel => 'MODELO PRÓPRIO';

  @override
  String get forecastTitle => 'ANÁLISE ESTATÍSTICA';

  @override
  String get forecastUnlocked => 'DESBLOQUEADO';

  @override
  String get forecastVerdictTitle => '💡  PARECER DO MODELO';

  @override
  String get formatScheduleUnavailable => 'Horário não disponível';

  @override
  String get groupBtts => 'AMBOS MARCAM';

  @override
  String get groupCards => 'CARTÕES';

  @override
  String get groupCorners => 'ESCANTEIOS';

  @override
  String get groupDoubleChance => 'DUPLA CHANCE';

  @override
  String get groupDrawNoBet => 'EMPATE ANULA APOSTA';

  @override
  String get groupFirstHalf => '1º TEMPO';

  @override
  String get groupGoals => 'GOLS';

  @override
  String get groupHandicap => 'HANDICAP';

  @override
  String get groupResult => 'RESULTADO';

  @override
  String get groupSpecials => 'ESPECIAIS';

  @override
  String get groupTeamGoals => 'GOLS DA EQUIPE';

  @override
  String get guideBody1 =>
      'Se um prognóstico tem 75% de probabilidade, o modelo espera que se cumpra cerca de 3 em cada 4 vezes que uma situação assim se repita. Isso significa que 1 em cada 4 não se cumprirá. Nenhum dado garante um resultado concreto.';

  @override
  String get guideBody2 =>
      'A cota é definida por uma casa de apostas e inclui a margem dela. Comparar a probabilidade do modelo com a implícita na cota ajuda a ver se o preço é razoável; não garante o resultado.';

  @override
  String get guideBody3 =>
      'Eles são publicados com sua probabilidade e cota de referência antes do início e não podem ser editados. Por isso você pode comparar a taxa de acerto histórica real com a prometida.';

  @override
  String get guideBody4 =>
      'Em uma múltipla, a probabilidade conjunta é o produto da de cada seleção, então cai rápido ao adicionar partidas. Uma cota alta costuma refletir justamente isso.';

  @override
  String get guideBody5 =>
      'Cada desafio avança por etapas e a seguinte só conta se a anterior for cumprida. Veja o progresso e o histórico, incluindo os desafios falhados, antes de seguir um.';

  @override
  String get guideBody6 =>
      'O QuantFut não é uma casa de apostas e não garante ganhos. Se decidir apostar, use apenas dinheiro que pode perder e somente se for maior de idade. Se o jogo deixar de ser um passatempo, peça ajuda.';

  @override
  String get guideHead1 => 'Uma probabilidade não é uma certeza';

  @override
  String get guideHead2 => 'A cota é um preço, não uma opinião do modelo';

  @override
  String get guideHead3 => 'Cada prognóstico é selado antes da partida';

  @override
  String get guideHead4 => 'Mais seleções, menos probabilidade';

  @override
  String get guideHead5 => 'Avança-se um degrau de cada vez';

  @override
  String get guideHead6 => 'É informação e entretenimento';

  @override
  String get guideSubtitle => 'Aprenda a ler os dados antes de decidir.';

  @override
  String get guideTitle => 'Guia de prognósticos';

  @override
  String get guideTopic1 => 'PROBABILIDADE';

  @override
  String get guideTopic2 => 'COTA';

  @override
  String get guideTopic3 => 'ALTA PROBABILIDADE';

  @override
  String get guideTopic4 => 'MÚLTIPLA';

  @override
  String get guideTopic5 => 'DESAFIO ESCADA';

  @override
  String get guideTopic6 => 'RESPONSABILIDADE';

  @override
  String get homeBannerClose => 'Fechar aviso';

  @override
  String get homeByDate => 'Jogos por data e horário';

  @override
  String get homeFeatured => 'Destaque do dia';

  @override
  String get homeFeedError =>
      'Não foi possível carregar os dados deste esporte.';

  @override
  String homeForecastAt(String when, String mexico) {
    return 'Prognóstico em $when ($mexico no México)';
  }

  @override
  String get homeForecastPending => 'Prognóstico pendente';

  @override
  String get homeMenuTooltip => 'Menu';

  @override
  String get homeNoMatchesDay => 'Não há partidas neste dia.';

  @override
  String get homePlayersWithPicks => 'Jogadores com prognóstico';

  @override
  String get homeSeeAll => 'Ver tudo';

  @override
  String homeTicketJoint(String percent) {
    return 'Prob. conjunta $percent';
  }

  @override
  String homeTicketLegs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count seleções',
      one: '$count seleção',
    );
    return '$_temp0';
  }

  @override
  String homeTicketOdds(String value) {
    return 'Cota $value';
  }

  @override
  String get homeTicketsEmpty => 'Ainda não há bilhetes hoje';

  @override
  String get homeTicketsTitle => 'Bilhetes do dia';

  @override
  String get homeToday => 'Hoje';

  @override
  String get homeTomorrow => 'Amanhã';

  @override
  String get imageCredits =>
      'Fotos: Wikimedia Commons (CC BY-SA). Autores na ficha de cada jogo.';

  @override
  String get imageUnavailable => 'Imagem indisponível';

  @override
  String get inboxEmpty => 'Você ainda não tem avisos.';

  @override
  String get inboxMatch => 'Jogo';

  @override
  String inboxSportTag(String sport) {
    return 'Esporte: $sport';
  }

  @override
  String get inboxTitle => 'Avisos';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count desafios em andamento',
      one: '1 desafio em andamento',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'saldo atual';

  @override
  String get ladderChance => 'de concluir';

  @override
  String get ladderEmpty => 'Não há desafios ativos publicados.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Estimativa: usa a probabilidade do degrau em jogo e a média dos demais ($avg). Não é garantia.';
  }

  @override
  String get ladderFreeHint => 'Um degrau grátis: o de maior probabilidade.';

  @override
  String get ladderHideSteps => 'Ocultar degraus';

  @override
  String get ladderHistoryDone => 'Concluído';

  @override
  String get ladderHistoryEmpty =>
      'Ainda não há desafios encerrados. Quando um terminar, aparecerá aqui com o resultado.';

  @override
  String get ladderHistoryExpired => 'Expirou sem ser concluído';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Falhou no degrau $step';
  }

  @override
  String ladderHistoryRate(String rate) {
    return 'Taxa de concluídos: $rate';
  }

  @override
  String ladderHistoryResult(String roi) {
    return 'Resultado acumulado: $roi';
  }

  @override
  String get ladderHistoryShown =>
      'Mostrando os últimos desafios concluídos e o último falhado.';

  @override
  String ladderHistorySummary(int done, int closed) {
    return '$done concluídos de $closed encerrados';
  }

  @override
  String get ladderHistoryTitle => 'Histórico de desafios';

  @override
  String get ladderNoteInPlay =>
      'Há um degrau aguardando resultado. O desafio continua vivo.';

  @override
  String get ladderNoteToPick =>
      'Falta escolher o próximo degrau; pode levar dias. O desafio continua vivo.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: 'faltam $remaining',
      one: 'falta 1',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Ver degraus';

  @override
  String get ladderStatusInPlay => 'Em jogo';

  @override
  String get ladderStatusToPick => 'A escolher';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps degraus',
      one: '$steps degrau',
    );
    return 'Desafio #$id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won de $goal ganhos';
  }

  @override
  String get languageFirstBadge => 'Configuração de idioma';

  @override
  String get languageFirstHint =>
      'Defina o idioma da análise para uma experiência melhor';

  @override
  String get languageFirstTitle => 'Selecione seu idioma';

  @override
  String get languageHint =>
      'Escolha o idioma. Ele fica guardado neste dispositivo e na sua conta.';

  @override
  String get languageTitle => 'Idioma do app';

  @override
  String get ledgerAd => 'Vídeo com recompensa';

  @override
  String get ledgerAttendance => 'Presença';

  @override
  String get ledgerInvitee => 'Prêmio de boas-vindas';

  @override
  String get ledgerOffer => 'Oferta concluída';

  @override
  String get ledgerReferralReversal => 'Prêmio de indicação revertido';

  @override
  String get ledgerReferrer => 'Prêmio por convidar';

  @override
  String get ledgerReversal => 'Oferta anulada';

  @override
  String get ledgerUnlock => 'Prognóstico desbloqueado';

  @override
  String get levelHigh => 'ALTA PROB.';

  @override
  String get levelModerate => 'MODERADA';

  @override
  String get levelSolid => 'SÓLIDA';

  @override
  String get lineAwayScores => 'Visitante marca · mais de 0,5 gols';

  @override
  String get lineDoubleChance => 'Dupla chance · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Handicap $line';
  }

  @override
  String get lineHomeScores => 'Mandante marca · mais de 0,5 gols';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'mais de $line escanteios',
      'other': 'menos de $line escanteios',
    });
    return '$team: $_temp0';
  }

  @override
  String get lineWinner => 'Vencedor · seleção de alta probabilidade';

  @override
  String get maintenanceNotice =>
      'Estamos realizando manutenção. Algumas funções podem demorar mais.';

  @override
  String get marketAwayScores => 'Visitante marca';

  @override
  String get marketBtts => 'Ambos marcam';

  @override
  String get marketCards => 'Cartões';

  @override
  String get marketCorners => 'Escanteios';

  @override
  String get marketCornersAway => 'Escanteios do visitante';

  @override
  String get marketCornersHome => 'Escanteios do mandante';

  @override
  String get marketDoubleChance => 'Dupla chance';

  @override
  String get marketGoals => 'Gols';

  @override
  String get marketGoalsAway => 'Gols do visitante';

  @override
  String get marketGoalsHome => 'Gols do mandante';

  @override
  String get marketHandicap => 'Handicap';

  @override
  String get marketHomeScores => 'Mandante marca';

  @override
  String get marketHtBtts => 'Ambos marcam no 1º tempo';

  @override
  String get marketHtGoal => 'Gol no 1º tempo';

  @override
  String marketOverLine(String line) {
    return 'Mais de $line';
  }

  @override
  String get marketResult1x2 => 'Resultado 1X2';

  @override
  String get marketUnknown => 'Mercado';

  @override
  String get marketWinToNil => 'Vence sem sofrer gol';

  @override
  String get marketsAndResults => 'Mercados e resultados';

  @override
  String marketsEvidenceAt(String date) {
    return 'Evidência em $date';
  }

  @override
  String get marketsFamiliesRadar => 'famílias de mercado no radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'acerto histórico $percent';
  }

  @override
  String marketsHitCount(int won, int resolved) {
    return '$won/$resolved publicados';
  }

  @override
  String get marketsInReview => 'Em revisão: sem linha confirmada';

  @override
  String get marketsModelActive => 'MODELO ATIVO';

  @override
  String get marketsNoLineLabel => 'sem linha confirmada';

  @override
  String get marketsNoPublications => 'Sem publicações ainda';

  @override
  String get marketsNoResolved => 'Sem prognósticos resolvidos';

  @override
  String marketsPublished(int won, int cases) {
    return 'Publicado $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases publicados acertados · $percent';
  }

  @override
  String get marketsRadarNote =>
      'O anel é o acerto histórico da melhor linha validada de cada mercado; «Publicado» são os prognósticos já resolvidos. São prognósticos pré-jogo, não alertas ao vivo, e nenhuma probabilidade garante um resultado.';

  @override
  String get marketsTabGame => 'Partida';

  @override
  String get marketsTabGames => 'Games';

  @override
  String get marketsTabPlayers => 'Jogadores';

  @override
  String get matchAwaitingResult => 'Aguardando resultado';

  @override
  String mdCornersTotal(Object total) {
    return 'escanteios · total $total';
  }

  @override
  String get mdEmptyHistory =>
      'Ainda não há prognósticos resolvidos neste mercado.';

  @override
  String get mdEmptyToday =>
      'Não há prognósticos disponíveis agora para este mercado. Aparecem quando o modelo os publica, antes do jogo.';

  @override
  String get mdHitRate => 'Taxa de acerto';

  @override
  String get mdLineConfirmed => 'Confirmada';

  @override
  String get mdLineNotDeployed => 'Não implantada';

  @override
  String get mdLineReview => 'Em revisão';

  @override
  String get mdLineShort => 'Amostra curta';

  @override
  String get mdLoadError => 'Não foi possível carregar o histórico.';

  @override
  String get mdModel => 'MODELO';

  @override
  String get mdNoDate => 'Sem data';

  @override
  String get mdOverall => 'Geral';

  @override
  String get mdTabPrevious => 'Anteriores';

  @override
  String mdTabToday(int count) {
    return 'Hoje ($count)';
  }

  @override
  String get mdValidatedLines => 'Linhas validadas';

  @override
  String get mmChance => 'OPORTUNIDADE';

  @override
  String get mmDisclaimer =>
      'É análise do modelo, não uma recomendação de aposta. «Odd justa» é 1/probabilidade: não é uma odd de casa de apostas. Um prognóstico pode falhar.';

  @override
  String get mmFairOdds => 'odd justa';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count mercados',
      one: '$count mercado',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count bloqueados',
      one: '$count bloqueado',
    );
    return '$_temp0';
  }

  @override
  String mmOpen(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count abertos',
      one: '$count aberto',
    );
    return '$_temp0';
  }

  @override
  String mmProb(int value) {
    return '$value% prob.';
  }

  @override
  String get mmPublishedOdds => 'odd publicada';

  @override
  String get mmScoresTitle => 'Placares mais prováveis';

  @override
  String get mmScoresVip => 'Os placares mais prováveis são para VIP.';

  @override
  String get mmTitle => 'Mercados da partida';

  @override
  String get moreApp => 'App';

  @override
  String get moreGuide => 'Guia de prognósticos';

  @override
  String get moreGuideSub => 'Como ler probabilidades, cotas e desafios';

  @override
  String get moreLearn => 'Aprenda';

  @override
  String get moreLegal => 'Legal';

  @override
  String get moreMySportsSub => 'Ordene e escolha quais esportes você vê';

  @override
  String get moreRate => 'Avaliar o app';

  @override
  String get moreRateSub => 'Compartilhe sua opinião';

  @override
  String get moreShare => 'Compartilhar o app';

  @override
  String get moreShareMessage =>
      'Conheça o QuantFut: probabilidades de futebol com dados, sem promessas. https://pronosticosdeportivos.pro';

  @override
  String get moreShareSub => 'Convide seus amigos';

  @override
  String get moreStoreError => 'Não foi possível abrir a loja de aplicativos.';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Início';

  @override
  String get navMarkets => 'Mercados';

  @override
  String get navPredictions => 'Prognósticos';

  @override
  String get navProfile => 'Perfil';

  @override
  String noteExpectedAverage(String value) {
    return 'Média esperada: $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Gols esperados: $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG: $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'As notificações do iOS aguardam a configuração da Apple.';

  @override
  String get notificationPermissionDenied =>
      'Ative a permissão nas configurações do dispositivo.';

  @override
  String get outcomeLoss => 'Errou';

  @override
  String get outcomePush => 'Reembolso';

  @override
  String get outcomeWin => 'Acertou';

  @override
  String parleyChipLine(int count, String min, String max) {
    return 'Até $count múltiplas · cota $min–$max';
  }

  @override
  String parleyDayCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count múltiplas',
      one: '$count múltipla',
    );
    return '$_temp0';
  }

  @override
  String parleyDaySettled(int won, int settled) {
    return '$won/$settled acertadas';
  }

  @override
  String get parleyDisclaimer =>
      'É escolhida por probabilidade, não por valor, e cada seleção reduz a margem. Uma múltipla pode falhar: multiplicar odds também multiplica o risco.';

  @override
  String get parleyFewNote =>
      'Com poucas múltiplas a taxa real ainda não prova nada.';

  @override
  String get parleyFreeChip => '1 grátis por dia';

  @override
  String get parleyFreeNote =>
      'Uma grátis por dia (a de menor odd); as demais, VIP.';

  @override
  String get parleyHistoryTitle => 'Histórico da Múltipla';

  @override
  String get parleyInactiveBody =>
      'Quando for ativada, você verá aqui as múltiplas do dia, seladas antes de os jogos começarem.';

  @override
  String get parleyInactiveTitle => 'A Múltipla ainda não está ativa';

  @override
  String get parleyInfoTitle => 'Como uma múltipla é escolhida';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs seleções',
      one: '$legs seleção',
    );
    return '$percent de probabilidade conjunta · $_temp0';
  }

  @override
  String get parleyLoadError => 'Não foi possível carregar a Múltipla.';

  @override
  String get parleyNoHistory =>
      'Ainda não há histórico de múltiplas. Aparecerá aqui quando a primeira for liquidada.';

  @override
  String get parleyNoneBody =>
      'O modelo não publica uma múltipla se não encontrar uma dentro das regras.';

  @override
  String get parleyNoneTitle => 'Hoje não há múltiplas';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Odd entre $min e $max';
  }

  @override
  String get parleyOutcomeLoss => 'Errou';

  @override
  String get parleyOutcomePending => 'Pendente';

  @override
  String get parleyOutcomeVoid => 'Anulada';

  @override
  String get parleyOutcomeWin => 'Acertou';

  @override
  String get parleyPastDays => 'Dias anteriores';

  @override
  String parleyRange(int count, String min, String max) {
    return 'De 1 a $count múltiplas · odd entre $min e $max · a mais provável de cada degrau';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Resultado $score';
  }

  @override
  String get parleySealed => 'Múltiplas seladas antes dos jogos';

  @override
  String parleyStep(Object step) {
    return 'DEGRAU $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total múltiplas acertadas';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' contra $value% prometido';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value% real';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Odd na publicação · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Probabilidade $percent';
  }

  @override
  String get pickSeeAnalysis => 'Ver análise da partida';

  @override
  String get pickSourceNA => 'Fonte não disponível';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Desbloquear por $cost moedas';
  }

  @override
  String get pickUnlockPrompt => 'Desbloqueie o prognóstico e sua odd.';

  @override
  String get pickUnlockVip => 'Desbloquear prognóstico VIP';

  @override
  String picksAllHeading(int count) {
    return 'Prognósticos · $count';
  }

  @override
  String get picksBestProb => 'Maior probabilidade';

  @override
  String picksCoinsShort(Object cost) {
    return '$cost moedas';
  }

  @override
  String get picksEmpty =>
      'Não há prognósticos publicados pendentes nesta faixa.';

  @override
  String picksFreeHeading(int count) {
    return 'Grátis · $count';
  }

  @override
  String get picksLockedHide => 'Ocultar a lista';

  @override
  String get picksLockedHint =>
      'Com VIP você vê o prognóstico, a probabilidade e a análise';

  @override
  String get picksLockedShow => 'Ver a lista';

  @override
  String picksLockedTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count prognósticos a mais com VIP',
      one: '1 prognóstico a mais com VIP',
    );
    return '$_temp0';
  }

  @override
  String picksRangeHint(int min, int max, int free) {
    return '$min–$max% de probabilidade · $free% grátis';
  }

  @override
  String get picksSeeAnalysis => 'Ver análise';

  @override
  String get picksTomorrow => 'Amanhã';

  @override
  String picksTrainingReasons(String reasons) {
    return 'Modelo em treinamento · $reasons';
  }

  @override
  String picksTrustDetail(int hits, int total) {
    return '$hits de $total prognósticos';
  }

  @override
  String picksTrustPromised(String percent) {
    return 'Prometido: $percent';
  }

  @override
  String get picksTrustTitle => 'Taxa de acerto histórica';

  @override
  String predictionsSealedAt(String when) {
    return 'Selado $when';
  }

  @override
  String get prefsAdsBody =>
      'Compartilha com a Meta dados criptografados da sua conta, do dispositivo e das suas compras para medir quais anúncios funcionam. Na Califórnia, desativá-lo equivale a «Não compartilhar meus dados».';

  @override
  String get prefsAdsTitle => 'Medição de anúncios (Meta)';

  @override
  String get prefsAnalyticsBody =>
      'Ajuda a melhorar o app com dados sobre as telas utilizadas. É opcional.';

  @override
  String get prefsAnalyticsTitle => 'Medição de uso';

  @override
  String get prefsDeleteAccount => 'Solicitar exclusão da minha conta';

  @override
  String get prefsDeleteAccountHint =>
      'Consulte as etapas e o contato da Saptain LTD.';

  @override
  String get prefsDiagnosticsBody =>
      'Envia informações técnicas ao Firebase e ao Sentry para diagnosticar falhas. É opcional.';

  @override
  String get prefsDiagnosticsTitle => 'Relatórios de erros e desempenho';

  @override
  String get prefsInbox => 'Caixa de avisos';

  @override
  String get prefsLanguageNote =>
      'O idioma se aplica a todo o app e fica guardado como preferência.';

  @override
  String get prefsNote =>
      'Você pode usar as funções básicas sem ativar medição ou diagnóstico. Alterar essas opções não apaga automaticamente os dados já enviados.';

  @override
  String get prefsNotificationsOff =>
      'Disponível quando o acesso com o Google for concluído.';

  @override
  String get prefsNotificationsOn =>
      'Você pode desativá-las quando quiser. Os avisos podem aparecer na tela bloqueada.';

  @override
  String get prefsNotificationsTitle => 'Notificações do QuantFut';

  @override
  String get prefsPrivacyRights => 'Privacidade e seus direitos';

  @override
  String get prefsTitle => 'Privacidade e preferências';

  @override
  String get privacyUpdateBody =>
      'Agora você pode assinar pelo Google Play ou pela App Store, e a medição de uso, o diagnóstico e a medição de anúncios da Meta vêm ativados. Você pode desativá-los em Preferências.';

  @override
  String get privacyUpdateOk => 'Entendi';

  @override
  String get privacyUpdateRead => 'Ler a política';

  @override
  String get privacyUpdateTitle => 'Atualizamos a privacidade';

  @override
  String get probBarAway => 'Fora';

  @override
  String get probBarDraw => 'Empate';

  @override
  String get probBarHome => 'Casa';

  @override
  String get profileAppVersion => 'Versão do app';

  @override
  String get profileBalance => 'Saldo e acompanhamento';

  @override
  String get profileCheckUpdate => 'Procurar atualização';

  @override
  String get profileConnected => 'QuantFut · Conectado ao servidor';

  @override
  String get profileCreateAccount => 'Criar conta';

  @override
  String get profileCreateOne => 'Criar uma conta';

  @override
  String get profileEmail => 'E-mail';

  @override
  String get profileEmailPending => 'E-mail pendente de verificação';

  @override
  String get profileEmailVerified => 'E-mail verificado';

  @override
  String get profileForgot => 'Esqueci minha senha';

  @override
  String get profileForgotSent =>
      'Se a conta existir, você receberá as instruções por e-mail.';

  @override
  String get profileFreePlan => 'Plano gratuito';

  @override
  String get profileGeneral => 'Geral';

  @override
  String get profileHaveAccount => 'Já tenho conta';

  @override
  String get profileLanguage => 'Idioma';

  @override
  String get profileMeasurement => 'Medição e erros';

  @override
  String get profileMySports => 'Meus esportes';

  @override
  String get profileMySportsDefault => 'padrão';

  @override
  String profileMySportsDown(String sport) {
    return 'Descer $sport';
  }

  @override
  String get profileMySportsHint =>
      'Use as setas para ordenar · o primeiro abre por padrão';

  @override
  String get profileMySportsLastVisible =>
      'Deixe pelo menos um esporte visível.';

  @override
  String get profileMySportsSaveError =>
      'Não foi possível salvar a alteração. Tente novamente.';

  @override
  String profileMySportsShow(String sport) {
    return 'Mostrar $sport';
  }

  @override
  String profileMySportsUp(String sport) {
    return 'Subir $sport';
  }

  @override
  String get profileNotifications => 'Notificações';

  @override
  String get profileOddsFormat => 'Formato das odds';

  @override
  String get profileOddsFormatValue =>
      'Decimal · Odds registradas na publicação';

  @override
  String get profilePassword => 'Senha';

  @override
  String get profilePreferences => 'Preferências';

  @override
  String get profileRefreshAccess => 'Atualizar meu acesso';

  @override
  String get profileSeePlans => 'Ver planos VIP';

  @override
  String get profileSendVerification => 'Enviar e-mail de verificação';

  @override
  String get profileSignIn => 'Entrar';

  @override
  String get profileSignOut => 'Sair';

  @override
  String get profileTitle => 'Perfil e configurações';

  @override
  String get profileUpToDate => 'Você já tem a versão mais recente.';

  @override
  String get profileUpdateCheckFailed =>
      'Não foi possível verificar se há atualização. Tente mais tarde.';

  @override
  String profileValidUntil(String date) {
    return 'Validade: $date';
  }

  @override
  String get profileVerificationSent => 'E-mail de verificação enviado.';

  @override
  String get profileVipActive => 'Acesso VIP ativo';

  @override
  String get profileYourAccount => 'Sua conta QuantFut';

  @override
  String resultLabel(String score) {
    return 'Resultado: $score';
  }

  @override
  String get rewardsAttendanceSub => 'Uma vez por dia · reinicia às 00:00 UTC';

  @override
  String get rewardsAttendanceTitle => 'Presença diária';

  @override
  String get rewardsAvailable => 'Disponível';

  @override
  String get rewardsCheckIn => 'Marcar presença';

  @override
  String get rewardsCheckInNote =>
      'Uma vez por dia UTC. Se você pular um dia, a sequência reinicia.';

  @override
  String rewardsChipRate(Object cost) {
    return '$cost moedas = 1 prognóstico';
  }

  @override
  String rewardsChipStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: 'Sequência de $days dias',
      one: 'Sequência de 1 dia',
    );
    return '$_temp0';
  }

  @override
  String rewardsClaimCta(Object coins) {
    return 'Marcar presença · +$coins';
  }

  @override
  String rewardsClaimed(Object coins) {
    return '+$coins moedas';
  }

  @override
  String get rewardsClaimedToday => 'Reivindicada hoje';

  @override
  String get rewardsCodeCopied => 'Código copiado.';

  @override
  String get rewardsCodeRegistered => 'Código de convite registrado.';

  @override
  String rewardsComingSoon(String names) {
    return 'Em breve: $names';
  }

  @override
  String get rewardsCopy => 'Copiar';

  @override
  String rewardsCopyCode(Object code) {
    return 'Copiar meu código · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Dia $number';
  }

  @override
  String get rewardsDebt => 'Saldo pendente por recompensas anuladas.';

  @override
  String get rewardsEarnTitle => 'Ganhe moedas hoje';

  @override
  String get rewardsEnough => 'Você tem moedas para um desbloqueio.';

  @override
  String get rewardsGo => 'Ir';

  @override
  String rewardsInviteChip(Object coins) {
    return '+$coins para você';
  }

  @override
  String rewardsInviteCondition(Object min) {
    return 'Após verificar o e-mail e concluir $min moedas em ofertas confirmadas.';
  }

  @override
  String rewardsInviteFriend(Object coins) {
    return 'Seu amigo recebe +$coins ao registrar seu código';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'Você +$referrer · Seu amigo +$invitee moedas';
  }

  @override
  String get rewardsInviteTitle => 'Convide seus amigos';

  @override
  String get rewardsInviterCode => 'Código de quem convidou você';

  @override
  String get rewardsLedgerEmpty => 'Ainda não há movimentações.';

  @override
  String get rewardsLedgerLess => 'Ver menos';

  @override
  String get rewardsLedgerMore => 'Ver mais';

  @override
  String get rewardsLedgerTitle => 'Minhas movimentações';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: 'Faltam $missing moedas para o seu próximo desbloqueio.',
      one: 'Falta $missing moeda para o seu próximo desbloqueio.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown =>
      'Faltam — moedas para o seu próximo desbloqueio.';

  @override
  String get rewardsMyCoins => 'Minhas moedas';

  @override
  String rewardsNextIn(String time) {
    return 'Próxima presença em $time';
  }

  @override
  String get rewardsOfferAvailable => 'Ofertas conforme seu país e dispositivo';

  @override
  String get rewardsOfferPending => 'Pendente de ativação';

  @override
  String get rewardsOffersConfig =>
      'Este provedor ainda não está pronto. Tente novamente mais tarde.';

  @override
  String get rewardsOffersCta => 'Ver ofertas';

  @override
  String get rewardsOffersLead => 'Complete ofertas e receba moedas.';

  @override
  String get rewardsOffersLoadFailed =>
      'Não foi possível abrir as ofertas. Verifique sua conexão e tente novamente.';

  @override
  String get rewardsOffersTimeout =>
      'As ofertas demoraram muito para carregar. Tente novamente.';

  @override
  String get rewardsOffersTitle => 'Ofertas para ganhar moedas';

  @override
  String get rewardsOffersUnavailable =>
      'Não há ofertas disponíveis agora. Tente novamente mais tarde.';

  @override
  String get rewardsOperationDone => 'Operação confirmada.';

  @override
  String get rewardsPaste => 'Colar código';

  @override
  String get rewardsPasteEmpty =>
      'Não há um código de convite na área de transferência.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered registrados · $qualified validados';
  }

  @override
  String get rewardsRefreshBalance => 'Atualizar saldo';

  @override
  String get rewardsRegisterCode => 'Registrar código';

  @override
  String get rewardsShare => 'Compartilhar meu código';

  @override
  String rewardsShareMessage(String code, String link) {
    return 'Use meu código de convite $code no QuantFut: em Coins, digite-o em “Código de quem convidou você”. Tudo explicado aqui: $link';
  }

  @override
  String get rewardsSignIn => 'Inicie sessão';

  @override
  String get rewardsSignInHint =>
      'Inicie sessão em Perfil para guardar seu saldo, marcar presença e usar um código de indicação.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days dias',
      one: '$days dia',
    );
    return 'Sequência de presença · $_temp0';
  }

  @override
  String get rewardsTermsTitle => 'Regras e condições';

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Desbloqueie um prognóstico por $cost moedas';
  }

  @override
  String rewardsUnlocksAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Você tem moedas para $count desbloqueios.',
      one: 'Você tem moedas para 1 desbloqueio.',
    );
    return '$_temp0';
  }

  @override
  String get sealLabel => 'SELO';

  @override
  String get sealPublished => 'PUBLICADO';

  @override
  String get sealVerified => 'VERIFICADO';

  @override
  String get selBttsNo => 'Ambos não marcam';

  @override
  String get selBttsYes => 'Ambos marcam';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Mais de $line cartões',
      'other': 'Menos de $line cartões',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Mais de $line escanteios',
      'other': 'Menos de $line escanteios',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Mais de $line escanteios de $team',
      'other': 'Menos de $line escanteios de $team',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team vence (empate devolve)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home ou $away (sem empate)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Mais de $line gols',
      'other': 'Menos de $line gols',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (handicap asiático)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return '$team vence';
  }

  @override
  String get selHtBttsNo => 'Ambos não marcam no 1T';

  @override
  String get selHtGoalYes => 'Haverá gol no 1T';

  @override
  String selTeamGoalsLine(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Mais de $line gols de $team',
      'other': 'Menos de $line gols de $team',
    });
    return '$_temp0';
  }

  @override
  String selTeamOrDraw(String team) {
    return '$team ou empate';
  }

  @override
  String selTeamScores(String team) {
    return '$team marca';
  }

  @override
  String selWinToNil(String team) {
    return '$team vence sem sofrer gol';
  }

  @override
  String get shellNeedCoinsBody =>
      'Ganhe moedas com a presença diária e as ofertas para desbloquear este prognóstico.';

  @override
  String get shellNeedCoinsCta => 'Ganhar moedas';

  @override
  String get shellNeedCoinsTitle => 'Faltam moedas';

  @override
  String get shellNewAlert => 'Novo aviso do QuantFut';

  @override
  String get shellSignInForCoins =>
      'Inicie sessão em Perfil para usar suas moedas.';

  @override
  String shellUnlockBody(Object cost) {
    return '$cost moedas serão descontadas do seu saldo. O acesso corresponde a este prognóstico.';
  }

  @override
  String get shellUnlockTitle => 'Desbloquear prognóstico';

  @override
  String get shellView => 'Ver';

  @override
  String get splashTagline => 'FUTEBOL · NBA · ESTATÍSTICA';

  @override
  String get sportAlertsNone => 'Sem avisos para esta partida.';

  @override
  String get sportAvailApplied => 'Relatório de lesões aplicado';

  @override
  String sportAvailListed(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count jogadores no relatório',
      one: '$count jogador no relatório',
    );
    return '$_temp0';
  }

  @override
  String sportAvailMissingMinutes(String team, String minutes) {
    return '$team: $minutes min de desfalques';
  }

  @override
  String sportAvailNotSubmitted(String team) {
    return '$team não enviou o relatório';
  }

  @override
  String get sportAvailPending => 'Relatório de lesões pendente';

  @override
  String get sportFootball => 'Futebol';

  @override
  String sportH2hRecord(String home, String away, int homeWins, int awayWins) {
    return '$home $homeWins – $awayWins $away';
  }

  @override
  String get sportMore => 'Mais';

  @override
  String get sportNba => 'NBA';

  @override
  String sportPhotoCredit(String name, String author, String license) {
    return 'Foto de $name: $author · $license';
  }

  @override
  String get sportSelectorLabel => 'Esporte';

  @override
  String get sportStatAge => 'Idade';

  @override
  String get sportStatAway => 'Fora';

  @override
  String get sportStatBackToBack => 'Jogo em dias seguidos';

  @override
  String get sportStatCareer => 'Carreira';

  @override
  String get sportStatFormIndex => 'Índice de forma';

  @override
  String get sportStatHome => 'Em casa';

  @override
  String get sportStatLast6 => 'Últimos 6';

  @override
  String get sportStatPointsAgainst => 'Pontos contra';

  @override
  String get sportStatPointsFor => 'Pontos a favor';

  @override
  String get sportStatRank => 'Ranking';

  @override
  String get sportStatRest => 'Dias de descanso';

  @override
  String get sportStatSeason => 'Temporada';

  @override
  String get sportStatStanding => 'Posição';

  @override
  String get sportStatStreak => 'Sequência';

  @override
  String get sportStatSurface => 'Neste piso';

  @override
  String get sportStatsUnavailable =>
      'Ainda não há estatísticas para esta partida.';

  @override
  String get sportSurfaceClay => 'Saibro';

  @override
  String get sportSurfaceGrass => 'Grama';

  @override
  String get sportSurfaceHard => 'Rápida';

  @override
  String get sportTennis => 'Tênis';

  @override
  String get startupFailed =>
      'Não foi possível iniciar o QuantFut. Tente novamente.';

  @override
  String get startupLoading => 'Iniciando o QuantFut';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Médias de $homeN jogos do mandante e $awayN do visitante. A cobertura de finalizações, escanteios e xG pode ser parcial.';
  }

  @override
  String get statBestAway => 'Melhor vitória fora';

  @override
  String get statBestHome => 'Melhor vitória em casa';

  @override
  String get statCleanSheet => 'Jogos sem sofrer gol';

  @override
  String get statCompareNote =>
      'As barras comparam os valores registrados; não representam probabilidades de vitória. Menos gols sofridos é melhor.';

  @override
  String get statCompareTitle => 'Comparação de equipes';

  @override
  String get statDrawStreak => 'Sequência de empates';

  @override
  String get statFormLegend =>
      'V: vitória · E: empate · D: derrota. Mais recente à esquerda.';

  @override
  String get statFormNA => 'Forma não disponível.';

  @override
  String get statFormTitle => 'Forma das equipes';

  @override
  String get statGoalsAgainst => 'Gols sofridos';

  @override
  String get statGoalsAvgNote =>
      'Gols marcados por jogo; não é a projeção de gols do modelo.';

  @override
  String get statGoalsAvgTitle => 'MÉDIA HISTÓRICA DE GOLS';

  @override
  String get statGoalsFor => 'Gols marcados';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'Em $n confrontos registrados: $home venceu $homeWins, $away venceu $awayWins e houve $draws empates.';
  }

  @override
  String get statH2hTitle => 'Confronto direto';

  @override
  String statLastMatches(int count) {
    return 'Últimos $count jogos registrados';
  }

  @override
  String get statMinutesNA =>
      'A distribuição por minutos não está disponível para este jogo.';

  @override
  String get statMinutesTitle => 'Gols por minuto';

  @override
  String get statNeedsAccess =>
      'O prognóstico deste jogo requer acesso VIP ou um desbloqueio com moedas.';

  @override
  String get statOnTargetShort => 'No alvo';

  @override
  String get statOver25 => 'Mais de 2,5 gols';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Probabilidade $percent · Odd @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played jogos';
  }

  @override
  String statPoints(Object points) {
    return '$points pontos';
  }

  @override
  String get statPoissonNA =>
      'A distribuição de Poisson e os placares prováveis ainda não estão disponíveis na entrega deste jogo.';

  @override
  String get statPoissonTitle => 'Distribuição de gols de Poisson';

  @override
  String statPosition(Object position) {
    return 'Posição $position';
  }

  @override
  String get statProbNA => 'Probabilidades do modelo ainda não disponíveis.';

  @override
  String get statProbTitle => 'PROBABILIDADE DE VITÓRIA · 1X2';

  @override
  String get statPublishedPick => 'PROGNÓSTICO PUBLICADO';

  @override
  String get statRadarNeeds =>
      'A comparação gráfica precisa de pelo menos três métricas disponíveis de ambas as equipes.';

  @override
  String get statRadarNote =>
      'Escala relativa por eixo. Uma área maior não implica maior probabilidade de vencer.';

  @override
  String get statResDraw => 'E';

  @override
  String get statResLoss => 'D';

  @override
  String get statResWin => 'V';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count resultados disponíveis',
      one: '$count resultado disponível',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Temporada e resultados recentes';

  @override
  String get statShots => 'Finalizações';

  @override
  String get statShotsOnTarget => 'Finalizações no alvo';

  @override
  String get statStandingNA => 'Classificação não disponível.';

  @override
  String get statSummaryTitle => 'Resumo do prognóstico';

  @override
  String get statTeamStatsTitle => 'Estatísticas da equipe';

  @override
  String get statWinStreak => 'Sequência de vitórias';

  @override
  String get statXgHistoric => 'xG histórico';

  @override
  String get streamHighProb => 'Alta probabilidade';

  @override
  String get streamLadder => 'Desafio Escada';

  @override
  String get streamParley => 'Múltipla';

  @override
  String tileFairOdds(String value) {
    return 'Odd justa $value';
  }

  @override
  String get tileFavorite => 'Favorito 1X2';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts pts';
  }

  @override
  String get tileFavoriteNA => 'Probabilidades não disponíveis';

  @override
  String get tileGoalsNA => 'Histórico insuficiente';

  @override
  String get tileGoalsTrend => 'Tendência de gols';

  @override
  String get tileOver25Model => 'Mais de 2,5 segundo o modelo';

  @override
  String get tileOver25Recent => 'Mais de 2,5 nos últimos jogos';

  @override
  String get tileProbability => 'Probabilidade';

  @override
  String get tileXg => 'xG projetado';

  @override
  String tileXgCaption(String home, String away) {
    return '$home mandante · $away visitante';
  }

  @override
  String get tileXgNA => 'Disponível em mercados de gols';

  @override
  String get titleAsianHandicap => 'Handicap asiático';

  @override
  String get titleDrawNoBet => 'Empate anula aposta';

  @override
  String titleTeamGoals(String team) {
    return 'Gols de $team';
  }

  @override
  String get titleTotalCards => 'Total de cartões';

  @override
  String get titleTotalCorners => 'Total de escanteios';

  @override
  String get titleTotalGoals => 'Total de gols';

  @override
  String get titleWinner => 'Vencedor da partida';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get updateLater => 'Mais tarde';

  @override
  String get updateNow => 'Atualizar agora';

  @override
  String get updateOptional => 'Uma nova versão do QuantFut está disponível.';

  @override
  String get updateRequired => 'Atualize o QuantFut para continuar.';

  @override
  String get updateStoreError =>
      'Não foi possível abrir a loja. Tente novamente.';

  @override
  String get updateTitle => 'Atualização disponível';

  @override
  String get vipAccessButton => 'Acesso VIP';

  @override
  String get vipActivate => 'Ativar acesso VIP';

  @override
  String get vipActive => 'Seu acesso VIP está ativo.';

  @override
  String get vipBadge => '✦  ACESSO VIP';

  @override
  String get vipBenefit1Body => 'Cada prognóstico é selado antes do jogo';

  @override
  String get vipBenefit1Title => 'Histórico verificável';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'Todos os prognósticos de $min a $max%, sem cota gratuita';
  }

  @override
  String get vipBenefit2Title => 'Alta Probabilidade completa';

  @override
  String get vipBenefit3Body => 'Todos os degraus pendentes, não apenas um';

  @override
  String get vipBenefit3Title => 'Desafio Escada completo';

  @override
  String get vipBenefit4Body =>
      'Odd publicada, probabilidade e xG de cada prognóstico';

  @override
  String get vipBenefit4Title => 'Odds e análise da partida';

  @override
  String get vipBenefitSportsBody =>
      'Partidas e jogadores, com os mesmos selos';

  @override
  String get vipBenefitSportsTitle => 'NBA e tênis incluídos';

  @override
  String get vipBestPrice => '★ MELHOR PREÇO';

  @override
  String get vipCheckAccess => 'Verificar meu acesso';

  @override
  String get vipCheckSignIn =>
      'Inicie sessão em Perfil para verificar seu acesso.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days dias',
      one: '$days dia',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Sua conta tem acesso gratuito.';

  @override
  String get vipGranted => 'Pronto! Seu acesso VIP está ativo.';

  @override
  String get vipHistoryNote =>
      'Histórico público e selado; as amostras por mercado são pequenas e um prognóstico pode falhar.';

  @override
  String get vipIntro =>
      'Todos os prognósticos de Alta Probabilidade e do Desafio Escada em futebol, NBA e tênis enquanto sua assinatura estiver vigente.';

  @override
  String get vipLinked => '🔒  Seu acesso VIP fica vinculado à sua conta';

  @override
  String get vipManage =>
      'Você já tem o Plus. Altere ou cancele seu plano na loja.';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/mês';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months meses',
      one: '$months mês',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'Sem vencimento';

  @override
  String get vipPaymentRequired =>
      'A contratação requer um canal de pagamento configurado.';

  @override
  String get vipPending =>
      'Pagamento pendente. Você terá acesso assim que a loja confirmar.';

  @override
  String get vipPickLabel => 'Prognóstico VIP';

  @override
  String get vipPlansSoon =>
      'Os planos serão exibidos quando estiverem disponíveis.';

  @override
  String get vipPricesNote => 'Preços do catálogo do servidor.';

  @override
  String get vipPurchasesPending =>
      'Compras em preparação: ainda nada é cobrado pelo app.';

  @override
  String get vipRestore => 'Restaurar compras';

  @override
  String get vipSportsNote =>
      'Cada prognóstico é selado antes da partida. «—»: ainda sem resultados para calculá-lo.';

  @override
  String get vipSportsTitle => 'Acerto registrado por esporte';

  @override
  String get vipStatRecorded => 'Taxa de acerto registrada';

  @override
  String get vipStatResolved => 'Resolvidos';

  @override
  String get vipStoreFailed =>
      'Não foi possível confirmar a compra. Tentaremos de novo quando você reabrir o app.';

  @override
  String get vipStoreTerms =>
      'Renova automaticamente pelo mesmo preço até você cancelar na loja.';

  @override
  String get vipStoreUnavailable =>
      'A loja não está disponível neste dispositivo.';

  @override
  String get vipSubscribe => 'Assinar';

  @override
  String get vipVerifying => 'Verificando a compra com a loja…';

  @override
  String get welcome1Body =>
      'Descubra o lado estatístico do esporte: jogos, análises e prognósticos do projeto que você já conhece na web.';

  @override
  String get welcome1Title => 'Futebol, NBA e tênis,\ncom outra perspectiva';

  @override
  String get welcome2Body =>
      'A forma recente, o confronto direto e as estatísticas ajudam a entender o que pode acontecer. Comece pelos dados.';

  @override
  String get welcome2Title => 'Cada jogo,\ncom mais contexto';

  @override
  String get welcome3Body =>
      'Gols, escanteios e handicap no futebol, props de jogadores na NBA e games no tênis. Saiba o que cada análise mede antes de interpretar uma seleção.';

  @override
  String get welcome3Title => 'Mais mercados.\nMais informação.';

  @override
  String get welcome4Body =>
      'Um prognóstico também se entende depois do jogo. O histórico permite comparar estimativas com resultados.';

  @override
  String get welcome4Title => 'Os resultados,\nà vista';

  @override
  String get welcome5Body =>
      'Uma probabilidade não é uma certeza. Explore o conteúdo, analise o contexto e forme seu próprio critério.';

  @override
  String get welcome5Title => 'Tudo começa\npor se informar';

  @override
  String welcomeGoTo(int number) {
    return 'Ir para a boas-vindas $number';
  }

  @override
  String get welcomeNext => 'Próximo';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Tela $page de $total';
  }

  @override
  String get welcomeSkip => 'Pular';

  @override
  String get welcomeStart => 'Começar';
}
