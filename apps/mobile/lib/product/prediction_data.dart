/// Presentation data. The backend must authorize private fields before delivery.
class PreviewMatch {
  const PreviewMatch(
    this.title,
    this.league,
    this.sport,
    this.dayOffset,
    this.probabilities,
    this.selection,
    this.secondary,
  ) : teaser = null;

  const PreviewMatch.vip(
    this.title,
    this.league,
    this.sport,
    this.dayOffset, {
    this.teaser,
  }) : probabilities = null,
       selection = null,
       secondary = null;

  final String title, league, sport;
  final int dayOffset;
  // These fields are absent from a locked payload, including its public teaser.
  final List<double>? probabilities;
  final String? selection, secondary;
  final PublicMatchTeaser? teaser;
  bool get locked => probabilities == null;
  List<String> get teams => title.split(' · ');
}

/// Only information explicitly classified as public by the server belongs here.
class PublicMatchTeaser {
  const PublicMatchTeaser(this.market, this.probability)
    : assert(probability >= 0 && probability <= 100);
  final String market;
  final double probability;
}
